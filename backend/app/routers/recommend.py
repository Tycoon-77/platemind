"""
recommend.py — Recommendation routes backed by pgvector + in-memory ML models.

POST /recommend/pantry  — pantry-match + hybrid LightGBM ranking.
POST /recommend/hybrid  — general personalised feed (MF collaborative filtering).

Architecture:
  - Recipe lookup and embedding similarity → Supabase / pgvector (real DB).
  - LightGBM hybrid ranker + MF model → ml_state (in-memory, fast).
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from app.limiter import limiter
from pydantic import BaseModel
import numpy as np
from sqlalchemy import text

from app import ml_state
from app.db import engine

router = APIRouter()


from typing import List, Optional

class PantryRecommendRequest(BaseModel):
    user_id: Optional[int] = None
    ingredients: List[str]
    dietary_tags: List[str] = []   # hard filters, e.g. ["vegan", "gluten-free"]


class HybridRecommendRequest(BaseModel):
    user_id: Optional[int] = None
    dietary_tags: List[str] = []


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row) -> dict:
    return {
        "recipe_id": row.recipe_id,
        "name":      row.name,
        "minutes":   row.minutes,
        "tags":      list(row.tags or []),
        "ingredients": list(row.ingredients or []),
    }


def _fetch_recipes_by_ids(conn, recipe_ids: list[int]) -> dict:
    """Return {recipe_id: dict} for a list of ids via a single DB query."""
    if not recipe_ids:
        return {}
    result = conn.execute(
        text("SELECT recipe_id, name, minutes, tags, ingredients FROM recipes WHERE recipe_id = ANY(:ids)"),
        {"ids": recipe_ids},
    )
    return {row.recipe_id: _row_to_dict(row) for row in result}


def _vector_search(conn, query_vec: list[float], top_k: int = 1000) -> list[int]:
    """Return recipe_ids ordered by cosine distance to query_vec from pgvector."""
    vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"
    rows = conn.execute(
        text("""
            SELECT recipe_id
            FROM recipes
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """),
        {"vec": vec_str, "k": top_k},
    ).fetchall()
    return [r.recipe_id for r in rows]

def _apply_dietary_filter(conn, recipe_ids: list[int], tags: list[str]) -> list[int]:
    """Hard-filter: keep only recipes whose tags array contains ALL required tags."""
    if not tags:
        rows = conn.execute(
            text("SELECT recipe_id FROM recipes WHERE recipe_id = ANY(:ids)"),
            {"ids": recipe_ids}
        ).fetchall()
        return [r.recipe_id for r in rows]
    rows = conn.execute(
        text("""
            SELECT recipe_id FROM recipes
            WHERE recipe_id = ANY(:ids)
              AND tags @> CAST(:tags AS text[])
        """),
        {"ids": recipe_ids, "tags": tags},
    ).fetchall()
    return [r.recipe_id for r in rows]

# ---------------------------------------------------------------------------
# /recommend/pantry
# ---------------------------------------------------------------------------

@router.post("/pantry")
async def recommend_from_pantry(body: PantryRecommendRequest):
    """
    Rank recipes by pantry overlap (TF-IDF weighted) + CF score + embedding
    similarity.  Recipe data is fetched from pgvector; ranking is done with the
    LightGBM hybrid model kept in ml_state.
    """
    if ml_state.matcher is None or ml_state.hybrid_model is None:
        raise HTTPException(500, "ML models not loaded")

    pantry_norm = set(ml_state.normalize_many(body.ingredients))

    # Build a query embedding from the user's pantry text
    pantry_text = " ".join(body.ingredients)
    try:
        from sentence_transformers import SentenceTransformer
        _enc = SentenceTransformer("all-MiniLM-L6-v2")
        query_vec = _enc.encode(pantry_text).tolist()
    except Exception:
        query_vec = [0.0] * 384

    try:
        with engine.connect() as conn:
            # 1. Vector search → candidate recipe_ids from pgvector
            candidates = _vector_search(conn, query_vec, top_k=500)

            # 2. Hard dietary filter
            if body.dietary_tags:
                candidates = _apply_dietary_filter(conn, candidates, body.dietary_tags)

            # 3. Fetch full recipe rows
            recipes_map = _fetch_recipes_by_ids(conn, candidates)

        # 4. Score each candidate with hybrid features
        u_factor = np.zeros(64)
        if body.user_id in ml_state.mf_model.user_enc_.classes_:
            u_idx = int(ml_state.mf_model.user_enc_.transform([body.user_id])[0])
            u_factor = ml_state.mf_model.model_.user_factors[u_idx]

        X_pred, valid_ids, reasons = [], [], []

        for rid in candidates:
            if rid not in recipes_map:
                continue

            # CF score
            cf_score = 0.0
            if rid in ml_state.mf_model.item_enc_.classes_:
                i_idx = int(ml_state.mf_model.item_enc_.transform([rid])[0])
                cf_score = float(np.dot(u_factor, ml_state.mf_model.model_.item_factors[i_idx]))

            # Embedding similarity (use cached in-memory if available, else 0)
            emb_sim = 0.0
            if rid in ml_state.emb_dict:
                emb_sim = float(np.dot(query_vec / (np.linalg.norm(query_vec) + 1e-9),
                                       ml_state.emb_dict[rid] / (np.linalg.norm(ml_state.emb_dict[rid]) + 1e-9)))

            # Pantry score (inline TF-IDF weighted)
            recipe_ings_norm = set(ml_state.recipe_ings_norm.get(
                rid, ml_state.normalize_many(recipes_map[rid]["ingredients"])
            ))
            if recipe_ings_norm:
                intersection = pantry_norm & recipe_ings_norm
                int_w = sum(ml_state.matcher.get_idf(i) for i in intersection)
                tot_w = sum(ml_state.matcher.get_idf(i) for i in recipe_ings_norm)
                p_score = int_w / tot_w if tot_w > 0 else 0.0
            else:
                intersection = set()
                p_score = 0.0

            X_pred.append([cf_score, emb_sim, p_score])
            valid_ids.append(rid)
            reason = (
                f"Matches {len(intersection)} pantry ingredients: {', '.join(sorted(intersection))}"
                if intersection else "Recommended for you"
            )
            reasons.append(reason)

        if not X_pred:
            return {"user_id": body.user_id, "ingredients": body.ingredients, "results": []}

        scores = ml_state.hybrid_model.predict(np.array(X_pred))
        ranked = sorted(zip(valid_ids, scores, reasons), key=lambda x: x[1], reverse=True)[:10]

        results = []
        for rid, score, reason in ranked:
            rec = recipes_map[rid].copy()
            rec["match_reason"] = reason
            results.append(rec)

        return {
            "user_id": body.user_id,
            "ingredients": body.ingredients,
            "results": results,
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, detail=str(e))


# ---------------------------------------------------------------------------
# /recommend/hybrid
# ---------------------------------------------------------------------------

@router.post("/hybrid")
@limiter.limit("20/minute")
async def recommend_hybrid(request: Request, body: HybridRecommendRequest):
    """
    General personalised feed via MF collaborative filtering.
    Recipe metadata fetched from pgvector.
    """
    if ml_state.mf_model is None:
        raise HTTPException(500, "ML models not loaded")

    try:
        from scipy.sparse import csr_matrix

        n_items = ml_state.mf_model.model_.item_factors.shape[0]
        dummy = csr_matrix((1, n_items))

        u_idx = 0
        if body.user_id in ml_state.mf_model.user_enc_.classes_:
            u_idx = int(ml_state.mf_model.user_enc_.transform([body.user_id])[0])

        recs_idx, _ = ml_state.mf_model.model_.recommend(
            u_idx, dummy, N=20, filter_already_liked_items=False
        )
        original_rids = ml_state.mf_model.item_enc_.inverse_transform(recs_idx).tolist()

        with engine.connect() as conn:
            if body.dietary_tags:
                original_rids = _apply_dietary_filter(conn, original_rids, body.dietary_tags)
            recipes_map = _fetch_recipes_by_ids(conn, original_rids[:10])

        results = []
        for rid in original_rids[:10]:
            if rid in recipes_map:
                rec = recipes_map[rid].copy()
                rec["match_reason"] = "Highly rated by users like you (CF)"
                results.append(rec)

        return {"user_id": body.user_id, "results": results}

    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, detail=str(e))
