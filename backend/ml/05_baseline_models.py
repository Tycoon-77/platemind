"""
05_baseline_models.py — Baseline recommender models for PlateMind Phase 1.

Implements and saves four baseline recommenders:
  1. PopularityRecommender     — top-N by mean rating × rating count
  2. UserBasedCF               — cosine similarity on the user-item matrix
  3. ItemBasedCF               — cosine similarity on the item-item matrix
  4. MatrixFactorization        — ALS via the `implicit` library (treats
                                  ratings as implicit confidence weights)

Train/test split: leave-last-interaction-out per user (chronological).
  - Users with < 3 interactions are excluded (cold-start; handled separately).

Saves each fitted model to models/  as a pickle file.
Saves train/test split indices for reproducibility.

Run:
    python backend/ml/05_baseline_models.py

Outputs:
    models/popularity_model.pkl
    models/user_cf_model.pkl
    models/item_cf_model.pkl
    models/mf_model.pkl
    data/processed/train_interactions.parquet
    data/processed/test_interactions.parquet
"""

import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("PHASE 1 — Step 5: Baseline Models")
print("=" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Load & prepare data
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1/7] Loading cleaned interactions…")
i = pd.read_parquet(PROCESSED / "interactions_clean.parquet")
i["date"] = pd.to_datetime(i["date"], utc=False)

# For CF we need explicit signals.  Use rating > 0; treat 0 as missing.
# Keep even low ratings (1-2) — they carry signal (negative).
i_rated = i[i["rating"] > 0].copy()

# Filter cold-start: users and items with at least 3 interactions each
print("[2/7] Filtering cold-start users/items (min 3 interactions each)…")
user_counts = i_rated["user_id"].value_counts()
item_counts = i_rated["recipe_id"].value_counts()
warm_users = user_counts[user_counts >= 3].index
warm_items = item_counts[item_counts >= 3].index

i_warm = i_rated[
    i_rated["user_id"].isin(warm_users) & i_rated["recipe_id"].isin(warm_items)
].copy()

print(f"  Warm users: {i_warm['user_id'].nunique():,}")
print(f"  Warm items: {i_warm['recipe_id'].nunique():,}")
print(f"  Interactions: {len(i_warm):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 2.  Train / test split — leave-last-out (chronological per user)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/7] Train/test split (leave-last-out per user)…")
i_warm = i_warm.sort_values(["user_id", "date"])
test_idx = i_warm.groupby("user_id").tail(1).index
train_idx = i_warm.index.difference(test_idx)

train = i_warm.loc[train_idx].copy()
test  = i_warm.loc[test_idx].copy()

print(f"  Train: {len(train):,} | Test: {len(test):,}")

# Save splits
train.to_parquet(PROCESSED / "train_interactions.parquet", index=False)
test.to_parquet(PROCESSED / "test_interactions.parquet", index=False)

# ─────────────────────────────────────────────────────────────────────────────
# 3.  Build user-item matrix (for CF models)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/7] Building user-item matrix…")

user_enc = LabelEncoder().fit(train["user_id"])
item_enc = LabelEncoder().fit(train["recipe_id"])

def encode(df: pd.DataFrame, u_enc: LabelEncoder, i_enc: LabelEncoder) -> pd.DataFrame:
    df = df.copy()
    df = df[df["user_id"].isin(u_enc.classes_) & df["recipe_id"].isin(i_enc.classes_)]
    df["user_idx"] = u_enc.transform(df["user_id"])
    df["item_idx"] = i_enc.transform(df["recipe_id"])
    return df

train_enc = encode(train, user_enc, item_enc)

n_users = len(user_enc.classes_)
n_items = len(item_enc.classes_)
print(f"  Matrix shape: {n_users} users × {n_items} items")

# User-item matrix: rows = users, cols = items, values = ratings
user_item_matrix = csr_matrix(
    (train_enc["rating"].values, (train_enc["user_idx"].values, train_enc["item_idx"].values)),
    shape=(n_users, n_items),
)
# Item-user is just the transpose (for implicit ALS which expects item×user)
item_user_matrix = user_item_matrix.T.tocsr()

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Model 1 — Popularity Recommender
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5/7] Training baseline models…")
print("  [a] Popularity Recommender…")

class PopularityRecommender:
    """Ranks items by a Bayesian-smoothed score: (count / (count + C)) * mean + (C / (count + C)) * global_mean.
    Equivalent to IMDb-style weighted rating.  Keeps cold-start awareness."""

    def __init__(self, C: int = 50):
        self.C = C  # minimum vote count (regularisation strength)
        self.scores_: pd.Series = None      # recipe_id → score
        self.global_mean_: float = None

    def fit(self, df: pd.DataFrame) -> "PopularityRecommender":
        agg = df.groupby("recipe_id")["rating"].agg(["mean", "count"])
        m = self.global_mean_ = df["rating"].mean()
        C = self.C
        # Bayesian average
        agg["score"] = (agg["count"] * agg["mean"] + C * m) / (agg["count"] + C)
        self.scores_ = agg["score"].sort_values(ascending=False)
        return self

    def recommend(self, user_id=None, n: int = 10,
                  exclude_recipe_ids=None) -> list:
        """Return top-N recipe IDs (optionally excluding already-seen ones)."""
        scores = self.scores_.copy()
        if exclude_recipe_ids:
            scores = scores.drop(labels=[r for r in exclude_recipe_ids if r in scores.index],
                                 errors="ignore")
        return scores.head(n).index.tolist()


pop_model = PopularityRecommender(C=50).fit(train)
print(f"    Top-5 popular recipes: {pop_model.recommend(n=5)}")


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Model 2 — User-Based CF
# ─────────────────────────────────────────────────────────────────────────────
print("  [b] User-Based CF…")

from sklearn.metrics.pairwise import cosine_similarity

class UserBasedCF:
    """k-NN user-based collaborative filtering on normalised user-item matrix."""

    def __init__(self, k: int = 50):
        self.k = k
        self.user_item_: csr_matrix = None
        self.user_enc_: LabelEncoder = None
        self.item_enc_: LabelEncoder = None

    def fit(self, user_item: csr_matrix, user_enc: LabelEncoder,
            item_enc: LabelEncoder) -> "UserBasedCF":
        self.user_item_ = user_item
        self.user_enc_ = user_enc
        self.item_enc_ = item_enc
        print("    (Similarity computed on the fly per user to save memory)")
        return self

    def recommend(self, user_id, n: int = 10, exclude_recipe_ids=None) -> list:
        if user_id not in self.user_enc_.classes_:
            return []
        u_idx = self.user_enc_.transform([user_id])[0]
        
        # Compute similarity between target user and all others on the fly
        target_vec = self.user_item_[u_idx]
        sims = cosine_similarity(target_vec, self.user_item_, dense_output=True)[0]
        
        # Top-k neighbours (exclude self)
        k_idxs = np.argsort(sims)[::-1][1:self.k + 1]
        k_sims = sims[k_idxs]

        # Weighted sum of neighbour ratings
        neighbour_ratings = self.user_item_[k_idxs].toarray()
        weights = k_sims[:, np.newaxis]
        scores = (neighbour_ratings * weights).sum(axis=0)

        # Zero out items the user already rated
        seen_mask = self.user_item_[u_idx].toarray().flatten() > 0
        scores[seen_mask] = -np.inf

        if exclude_recipe_ids:
            for rid in exclude_recipe_ids:
                if rid in self.item_enc_.classes_:
                    idx = self.item_enc_.transform([rid])[0]
                    scores[idx] = -np.inf

        top_idxs = np.argsort(scores)[::-1][:n]
        return self.item_enc_.inverse_transform(top_idxs).tolist()


ubcf = UserBasedCF(k=50).fit(user_item_matrix, user_enc, item_enc)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Model 3 — Item-Based CF
# ─────────────────────────────────────────────────────────────────────────────
print("  [c] Item-Based CF…")

class ItemBasedCF:
    """k-NN item-based collaborative filtering on the item-user matrix."""

    def __init__(self, k: int = 50):
        self.k = k
        self.user_item_: csr_matrix = None
        self.user_enc_: LabelEncoder = None
        self.item_enc_: LabelEncoder = None

    def fit(self, user_item: csr_matrix, user_enc: LabelEncoder,
            item_enc: LabelEncoder) -> "ItemBasedCF":
        self.user_item_ = user_item
        self.user_enc_ = user_enc
        self.item_enc_ = item_enc
        print("    (Similarity computed on the fly per user's rated items to save memory)")
        return self

    def recommend(self, user_id, n: int = 10, exclude_recipe_ids=None) -> list:
        if user_id not in self.user_enc_.classes_:
            return []
        u_idx = self.user_enc_.transform([user_id])[0]
        user_vec = self.user_item_[u_idx].toarray().flatten()

        # Items the user has rated
        rated_idxs = np.where(user_vec > 0)[0]
        if len(rated_idxs) == 0:
            return []

        # We only need similarities for the items this user has rated vs all items.
        # Compute on the fly: shape will be (len(rated_idxs), n_items)
        rated_item_vecs = self.user_item_[:, rated_idxs].T
        # Compute cosine similarity between rated items and ALL items
        sims = cosine_similarity(rated_item_vecs, self.user_item_.T, dense_output=True)

        # For each rated item, weight similarities by the user's rating
        scores = np.zeros(self.user_item_.shape[1])
        for i, i_idx in enumerate(rated_idxs):
            rating = user_vec[i_idx]
            scores += sims[i] * rating

        # Zero out already-rated items
        scores[rated_idxs] = -np.inf

        if exclude_recipe_ids:
            for rid in exclude_recipe_ids:
                if rid in self.item_enc_.classes_:
                    idx = self.item_enc_.transform([rid])[0]
                    scores[idx] = -np.inf

        top_idxs = np.argsort(scores)[::-1][:n]
        return self.item_enc_.inverse_transform(top_idxs).tolist()


ibcf = ItemBasedCF(k=50).fit(user_item_matrix, user_enc, item_enc)


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Model 4 — Matrix Factorization via implicit ALS
#     implicit expects confidence = 1 + alpha * rating for positive entries.
# ─────────────────────────────────────────────────────────────────────────────
print("  [d] Matrix Factorization (ALS via implicit)…")

try:
    import implicit
    from implicit.als import AlternatingLeastSquares

    class MatrixFactorization:
        def __init__(self, factors: int = 64, iterations: int = 30,
                     regularization: float = 0.05, alpha: float = 40.0):
            self.factors = factors
            self.iterations = iterations
            self.regularization = regularization
            self.alpha = alpha
            self.model_: AlternatingLeastSquares = None
            self.user_enc_: LabelEncoder = None
            self.item_enc_: LabelEncoder = None
            self.user_item_: csr_matrix = None

        def fit(self, user_item: csr_matrix, user_enc: LabelEncoder,
                item_enc: LabelEncoder) -> "MatrixFactorization":
            self.user_enc_ = user_enc
            self.item_enc_ = item_enc
            self.user_item_ = user_item

            # Confidence weighting: C_ui = 1 + alpha * rating
            # implicit >= 0.5 expects (users, items) matrix
            confidence = user_item.copy()
            confidence.data = 1.0 + self.alpha * confidence.data

            self.model_ = AlternatingLeastSquares(
                factors=self.factors,
                iterations=self.iterations,
                regularization=self.regularization,
                use_gpu=False,
            )
            self.model_.fit(confidence)
            return self

        def recommend(self, user_id, n: int = 10, exclude_recipe_ids=None) -> list:
            if user_id not in self.user_enc_.classes_:
                return []
            u_idx = int(self.user_enc_.transform([user_id])[0])
            # Recommend expects (userid, user_items row)
            recs, _ = self.model_.recommend(
                u_idx, self.user_item_[u_idx], N=n + 20, filter_already_liked_items=True
            )
            rec_ids = self.item_enc_.inverse_transform(recs).tolist()
            if exclude_recipe_ids:
                rec_ids = [r for r in rec_ids if r not in exclude_recipe_ids]
            return rec_ids[:n]

    mf_model = MatrixFactorization(
        factors=64, iterations=30, regularization=0.05, alpha=40.0
    ).fit(user_item_matrix, user_enc, item_enc)
    mf_ok = True
    print("    ALS training complete.")

except Exception as e:
    print(f"    ⚠️  ALS failed ({e}) — saving None placeholder.")
    mf_model = None
    mf_ok = False


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Save all models
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6/7] Saving models…")

def save_model(obj, path: Path) -> None:
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    kb = path.stat().st_size / 1024
    print(f"  ✓ {path.name} ({kb:.0f} KB)")

save_model(pop_model,  MODELS_DIR / "popularity_model.pkl")
save_model(ubcf,       MODELS_DIR / "user_cf_model.pkl")
save_model(ibcf,       MODELS_DIR / "item_cf_model.pkl")
save_model(mf_model,   MODELS_DIR / "mf_model.pkl")

# Also save encoders (needed at inference time)
save_model({"user_enc": user_enc, "item_enc": item_enc},
           MODELS_DIR / "encoders.pkl")

print("\n✅  05_baseline_models.py complete.")
