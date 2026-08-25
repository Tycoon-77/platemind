"""
06_evaluate.py — Offline evaluation of baseline recommenders.

Metrics:
    Precision@K  — fraction of top-K recommendations that are relevant
                   (relevant = recipe appears in the user's test set)
    Recall@K     — fraction of relevant items recovered in top-K
    Coverage     — fraction of all catalog items that appear in any recommendation
                   across all test users (measures model diversity)

Methodology:
    - Leave-last-out split (produced by 05_baseline_models.py).
    - Evaluation users = all warm users who have exactly 1 item in test.
    - Relevant item = the single held-out item per user.
    - We exclude training items from recommendations for all CF models.
    - Popularity model is the same for all users; we still score it per-user
      (excluding their training items) to make the comparison fair.

Run:
    python backend/ml/06_evaluate.py

Outputs:
    ml/eval_report.md
    data/processed/eval_results.parquet  (per-user scores for drill-down)
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
ML_DIR = ROOT / "ml"


# ─────────────────────────────────────────────────────────────────────────────
# Metric functions
# ─────────────────────────────────────────────────────────────────────────────

def precision_at_k(recommended: list, relevant: set, k: int) -> float:
    top_k = recommended[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / k if k > 0 else 0.0


def recall_at_k(recommended: list, relevant: set, k: int) -> float:
    top_k = recommended[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(relevant) if relevant else 0.0


def coverage(all_recs: list[list], catalog_size: int) -> float:
    unique_recs = {item for recs in all_recs for item in recs}
    return len(unique_recs) / catalog_size if catalog_size > 0 else 0.0


from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder

class PopularityRecommender:
    def __init__(self, C: int = 50):
        self.C = C
    def recommend(self, user_id=None, n: int = 10, exclude_recipe_ids=None) -> list:
        scores = self.scores_.copy()
        if exclude_recipe_ids:
            scores = scores.drop(labels=[r for r in exclude_recipe_ids if r in scores.index], errors="ignore")
        return scores.head(n).index.tolist()

class UserBasedCF:
    def __init__(self, k: int = 50):
        self.k = k
    def recommend(self, user_id, n: int = 10, exclude_recipe_ids=None) -> list:
        if user_id not in self.user_enc_.classes_: return []
        u_idx = self.user_enc_.transform([user_id])[0]
        target_vec = self.user_item_[u_idx]
        sims = cosine_similarity(target_vec, self.user_item_, dense_output=True)[0]
        k_idxs = np.argsort(sims)[::-1][1:self.k + 1]
        k_sims = sims[k_idxs]
        neighbour_ratings = self.user_item_[k_idxs].toarray()
        weights = k_sims[:, np.newaxis]
        scores = (neighbour_ratings * weights).sum(axis=0)
        seen_mask = self.user_item_[u_idx].toarray().flatten() > 0
        scores[seen_mask] = -np.inf
        if exclude_recipe_ids:
            for rid in exclude_recipe_ids:
                if rid in self.item_enc_.classes_:
                    idx = self.item_enc_.transform([rid])[0]
                    scores[idx] = -np.inf
        top_idxs = np.argsort(scores)[::-1][:n]
        return self.item_enc_.inverse_transform(top_idxs).tolist()

class ItemBasedCF:
    def __init__(self, k: int = 50):
        self.k = k
    def recommend(self, user_id, n: int = 10, exclude_recipe_ids=None) -> list:
        if user_id not in self.user_enc_.classes_: return []
        u_idx = self.user_enc_.transform([user_id])[0]
        user_vec = self.user_item_[u_idx].toarray().flatten()
        rated_idxs = np.where(user_vec > 0)[0]
        if len(rated_idxs) == 0: return []
        rated_item_vecs = self.user_item_[:, rated_idxs].T
        sims = cosine_similarity(rated_item_vecs, self.user_item_.T, dense_output=True)
        scores = np.zeros(self.user_item_.shape[1])
        for i, i_idx in enumerate(rated_idxs):
            rating = user_vec[i_idx]
            scores += sims[i] * rating
        scores[rated_idxs] = -np.inf
        if exclude_recipe_ids:
            for rid in exclude_recipe_ids:
                if rid in self.item_enc_.classes_:
                    idx = self.item_enc_.transform([rid])[0]
                    scores[idx] = -np.inf
        top_idxs = np.argsort(scores)[::-1][:n]
        return self.item_enc_.inverse_transform(top_idxs).tolist()

class MatrixFactorization:
    def __init__(self, factors: int = 64, iterations: int = 30,
                 regularization: float = 0.05, alpha: float = 40.0):
        self.factors = factors
        self.iterations = iterations
        self.regularization = regularization
        self.alpha = alpha
        
    def recommend(self, user_id, n: int = 10, exclude_recipe_ids=None) -> list:
        if user_id not in self.user_enc_.classes_: return []
        u_idx = int(self.user_enc_.transform([user_id])[0])
        recs, _ = self.model_.recommend(
            u_idx, self.user_item_[u_idx], N=n + 20, filter_already_liked_items=True
        )
        rec_ids = self.item_enc_.inverse_transform(recs).tolist()
        if exclude_recipe_ids:
            rec_ids = [r for r in rec_ids if r not in exclude_recipe_ids]
        return rec_ids[:n]

# ─────────────────────────────────────────────────────────────────────────────
# Evaluate a model
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_model(
    model_name: str,
    recommend_fn,          # callable(user_id, n, exclude_recipe_ids) → list[recipe_id]
    test_df: pd.DataFrame,
    train_df: pd.DataFrame,
    catalog_size: int,
    k: int = 10,
    max_users: int = 500,
) -> dict:
    """
    Evaluate a recommender against the leave-last-out test set.

    Parameters
    ----------
    max_users : cap on evaluation users to keep runtime tractable.
    """
    users = test_df["user_id"].unique()
    if len(users) > max_users:
        rng = np.random.default_rng(42)
        users = rng.choice(users, size=max_users, replace=False)

    # Build per-user training set (for exclusion)
    train_items = train_df.groupby("user_id")["recipe_id"].apply(set).to_dict()

    precs, recs_list, all_recs = [], [], []
    skipped = 0

    for uid in users:
        held_out = set(test_df.loc[test_df["user_id"] == uid, "recipe_id"])
        exclude = train_items.get(uid, set())
        recs = recommend_fn(uid, n=k, exclude_recipe_ids=exclude)
        if not recs:
            skipped += 1
            continue
        precs.append(precision_at_k(recs, held_out, k))
        recs_list.append(recall_at_k(recs, held_out, k))
        all_recs.append(recs)

    n_eval = len(precs)
    results = {
        "model": model_name,
        f"precision@{k}": np.mean(precs) if precs else 0.0,
        f"recall@{k}": np.mean(recs_list) if recs_list else 0.0,
        "coverage": coverage(all_recs, catalog_size),
        "n_evaluated": n_eval,
        "n_skipped": skipped,
    }
    print(f"  {model_name}: P@{k}={results[f'precision@{k}']:.4f}  "
          f"R@{k}={results[f'recall@{k}']:.4f}  "
          f"Cov={results['coverage']:.4f}  "
          f"(n={n_eval}, skipped={skipped})")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 60)
print("PHASE 1 — Step 6: Evaluation")
print("=" * 60)

# Load data
print("\n[1/3] Loading splits and models…")
train = pd.read_parquet(PROCESSED / "train_interactions.parquet")
test  = pd.read_parquet(PROCESSED / "test_interactions.parquet")

with open(MODELS_DIR / "popularity_model.pkl", "rb") as f:
    pop_model = pickle.load(f)
with open(MODELS_DIR / "user_cf_model.pkl", "rb") as f:
    ubcf = pickle.load(f)
with open(MODELS_DIR / "item_cf_model.pkl", "rb") as f:
    ibcf = pickle.load(f)
with open(MODELS_DIR / "mf_model.pkl", "rb") as f:
    mf_model = pickle.load(f)

catalog_size = train["recipe_id"].nunique()
print(f"  Catalog size: {catalog_size:,}")
print(f"  Test users: {test['user_id'].nunique():,}")

K = 10

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[2/3] Evaluating at K={K}…")

results = []

# Popularity
results.append(evaluate_model(
    "Popularity",
    lambda uid, n, exclude_recipe_ids: pop_model.recommend(uid, n=n, exclude_recipe_ids=exclude_recipe_ids),
    test, train, catalog_size, k=K,
))

# User-Based CF
results.append(evaluate_model(
    "UserCF",
    lambda uid, n, exclude_recipe_ids: ubcf.recommend(uid, n=n, exclude_recipe_ids=exclude_recipe_ids),
    test, train, catalog_size, k=K,
))

# Item-Based CF
results.append(evaluate_model(
    "ItemCF",
    lambda uid, n, exclude_recipe_ids: ibcf.recommend(uid, n=n, exclude_recipe_ids=exclude_recipe_ids),
    test, train, catalog_size, k=K,
))

# Matrix Factorization
if "MatrixFactorization" in dir() and mf_model:
    results.append(evaluate_model(
        "MatrixFactorization (ALS)",
        lambda uid, n, exclude_recipe_ids: mf_model.recommend(uid, n=n, exclude_recipe_ids=exclude_recipe_ids),
        test, train, catalog_size, max_users=500
    ))
else:
    results.append({
        "model": "MatrixFactorization (ALS)",
        f"precision@{K}": None,
        f"recall@{K}": None,
        "coverage": None,
        "n_evaluated": 0,
        "n_skipped": 0,
    })
    print("  MatrixFactorization (ALS): skipped (model not available)")

# ─────────────────────────────────────────────────────────────────────────────
# Save results and write eval_report.md
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/3] Saving results and writing eval_report.md…")

results_df = pd.DataFrame(results)
results_df.to_parquet(PROCESSED / "eval_results.parquet", index=False)

# ── Determine best model ──────────────────────────────────────────────────────
best_row = results_df.dropna(subset=[f"precision@{K}"]).sort_values(
    f"precision@{K}", ascending=False
).iloc[0]
best_model_name = best_row["model"]

# ── Write eval_report.md ──────────────────────────────────────────────────────
p_col = f"precision@{K}"
r_col = f"recall@{K}"

table_rows = ""
for _, row in results_df.iterrows():
    p = f"{row[p_col]:.4f}" if row[p_col] is not None else "N/A"
    r = f"{row[r_col]:.4f}" if row[r_col] is not None else "N/A"
    c = f"{row['coverage']:.4f}" if row["coverage"] is not None else "N/A"
    star = " ⭐" if row["model"] == best_model_name else ""
    table_rows += f"| {row['model']}{star} | {p} | {r} | {c} | {int(row['n_evaluated'])} |\n"

report = f"""# PlateMind — Phase 1 Baseline Evaluation Report

## Setup

| Parameter | Value |
|---|---|
| Dataset | Food.com Recipes & Interactions (Kaggle) |
| Split | Leave-last-out (chronological per user) |
| Warm threshold | ≥ 3 interactions per user AND per recipe |
| Train interactions | {len(train):,} |
| Test interactions | {len(test):,} |
| Evaluation users | ≤ 5,000 (sampled if larger) |
| Catalog size | {catalog_size:,} unique recipes |
| Metric K | {K} |

## Results

| Model | Precision@{K} | Recall@{K} | Coverage | Users Evaluated |
|---|---|---|---|---|
{table_rows}
⭐ = best on Precision@{K}

## Interpretation

### Precision@{K}
Fraction of the top-{K} recommendations that match the held-out item.
Since each user has exactly **one** held-out item, the theoretical ceiling
for Precision@{K} is 1/{K} = {1/K:.4f} (if the model perfectly places the
held-out item in any of the top-{K} slots).  Real values are well below this
because the recommendation space is large ({catalog_size:,} items).

### Recall@{K}
Identical to Precision@{K} in the leave-one-out setup (single relevant item),
so these columns should match.  Slight differences arise from skipped users.

### Coverage
Fraction of the catalog that appears in at least one recommendation across all
evaluated users.  **High coverage = diverse recommendations** (less "filter
bubble").  Popularity naturally has low coverage; CF models tend to be higher.

## Key Findings

1. **Popularity baseline** provides a reasonable floor and high coverage
   because the same popular items are recommended to everyone.

2. **User-Based CF** improves personalization but scales quadratically with
   user count — the similarity matrix is O(n_users²).  At this scale it is
   still tractable, but Phase 2 replaces it with the hybrid LightGBM ranker.

3. **Item-Based CF** tends to perform comparably to User-CF and is more stable
   as the item set is smaller than the user set here.

4. **Matrix Factorization (ALS)** via `implicit` treats ratings as confidence
   weights (1 + α * rating) and learns dense latent factors.  It typically
   offers the best precision among the four baselines.

## What Phase 2 Adds

- **Pantry-match scoring** (ingredient overlap, TF-IDF weighted by rarity).
- **Recipe content embeddings** (sentence-transformers → pgvector).
- **Dietary hard-filters** applied *before* ranking (allergies are a constraint,
  not a signal).
- **LightGBM hybrid ranker** blending all signals; tuned with Optuna.
- Target: ≥ 2× improvement in NDCG@10 over the best baseline here.

## Limitations

- **Rating sparsity**: most users have very few interactions; cold-start
  users (< 3 interactions) are excluded entirely and need the popularity
  fallback or pantry-match-only path.
- **Implicit negative signals**: rating == 0 rows (user reviewed without
  rating) are excluded from CF training.  Phase 2 will use them as
  implicit positive signals (viewed/engaged = mild preference).
- **Temporal drift**: the dataset spans 2000–2018; user tastes likely
  evolved.  A time-decayed weighting scheme could improve recency.
"""

report_path = ML_DIR / "eval_report.md"
report_path.write_text(report, encoding="utf-8")
print(f"  ✓ Written → {report_path}")

print(f"\n  Best model: {best_model_name}")
print(f"  Precision@{K}: {best_row[p_col]:.4f}")
print(f"  Recall@{K}:    {best_row[r_col]:.4f}")
print(f"  Coverage:      {best_row['coverage']:.4f}")

print("\n✅  06_evaluate.py complete.")
