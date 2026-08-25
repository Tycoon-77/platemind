"""
pantry.py — User pantry CRUD backed by Supabase Postgres.

GET    /pantry/{user_id}                 — List all pantry items.
POST   /pantry/{user_id}                 — Add ingredient (normalised).
DELETE /pantry/{user_id}/{ingredient_id} — Remove item by id.

Auth required on all routes. user_id in path must match token owner.
"""
from __future__ import annotations
import sys, importlib.util
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db import engine
from app.auth_deps import require_auth, CurrentUser

router = APIRouter()

# ─── Ingredient normaliser (reuse Phase 1 function) ──────────────────────────

_normalise_cache: dict = {}

def _get_normaliser():
    if "normalise" not in _normalise_cache:
        spec = importlib.util.spec_from_file_location(
            "normalise_mod",
            Path(__file__).resolve().parents[2] / "ml" / "02_normalize_ingredients.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _normalise_cache["normalise"] = mod.normalize_ingredient
    return _normalise_cache["normalise"]


def _norm(raw: str) -> str:
    try:
        return _get_normaliser()(raw)
    except Exception:
        return raw.lower().strip()


# ─── Schema ──────────────────────────────────────────────────────────────────

class AddIngredientRequest(BaseModel):
    ingredient: str


# ─── Routes ──────────────────────────────────────────────────────────────────

def _check_owner(user_id: int, current_user: CurrentUser):
    if current_user["user_id"] != user_id:
        raise HTTPException(403, "Access denied: token does not match user_id")


@router.get("/{user_id}")
async def get_pantry(user_id: int, current_user: CurrentUser = Depends(require_auth)):
    _check_owner(user_id, current_user)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, ingredient_raw, ingredient_norm, added_at
            FROM pantry_items WHERE user_id = :uid ORDER BY added_at DESC
        """), {"uid": user_id}).fetchall()
    return {
        "user_id": user_id,
        "items": [
            {"id": r.id, "ingredient_raw": r.ingredient_raw,
             "ingredient_norm": r.ingredient_norm, "added_at": str(r.added_at)}
            for r in rows
        ],
    }


@router.post("/{user_id}", status_code=201)
async def add_to_pantry(
    user_id: int,
    body: AddIngredientRequest,
    current_user: CurrentUser = Depends(require_auth),
):
    _check_owner(user_id, current_user)
    norm = _norm(body.ingredient)
    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO pantry_items (user_id, ingredient_raw, ingredient_norm)
            VALUES (:uid, :raw, :norm)
            ON CONFLICT (user_id, ingredient_norm) DO UPDATE SET ingredient_raw = EXCLUDED.ingredient_raw
            RETURNING id, ingredient_raw, ingredient_norm
        """), {"uid": user_id, "raw": body.ingredient, "norm": norm}).fetchone()
    return {
        "user_id":         user_id,
        "id":              row.id,
        "ingredient_raw":  row.ingredient_raw,
        "ingredient_norm": row.ingredient_norm,
    }


@router.delete("/{user_id}/{ingredient_id}", status_code=200)
async def remove_from_pantry(
    user_id: int,
    ingredient_id: int,
    current_user: CurrentUser = Depends(require_auth),
):
    _check_owner(user_id, current_user)
    with engine.begin() as conn:
        result = conn.execute(text("""
            DELETE FROM pantry_items WHERE id = :iid AND user_id = :uid
        """), {"iid": ingredient_id, "uid": user_id})
    if result.rowcount == 0:
        raise HTTPException(404, "Pantry item not found")
    return {"deleted": ingredient_id}
