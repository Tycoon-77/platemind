"""
04_user_features.py — RFM-style user feature engineering for PlateMind.

Computes per-user features from the cleaned interaction history.
These features are used as input columns in the Phase 2 LightGBM hybrid ranker.

RFM Features:
    Recency   — days since last interaction (lower = more recent)
    Frequency — total number of interactions
    Monetary  — mean rating (proxy for engagement "value")

Additional features:
    rating_count    — interactions with an explicit rating (rating > 0)
    rating_mean     — mean of explicit ratings
    rating_std      — std of explicit ratings (preference consistency)
    rating_min/max  — range of explicit ratings
    pct_5star       — fraction of rated recipes given 5 stars
    pct_low         — fraction rated 1–2 stars
    days_active     — days between first and last interaction
    recipes_per_day — frequency / days_active (activity density)
    unique_recipes  — number of distinct recipes interacted with

Run:
    python backend/ml/04_user_features.py

Outputs:
    data/processed/user_features.parquet
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

print("=" * 60)
print("PHASE 1 — Step 4: User Feature Engineering (RFM)")
print("=" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# Load
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1/3] Loading interactions…")
i = pd.read_parquet(PROCESSED / "interactions_clean.parquet")
i["date"] = pd.to_datetime(i["date"], utc=False)
print(f"  {len(i):,} interactions, {i['user_id'].nunique():,} users")

REFERENCE_DATE = i["date"].max()
print(f"  Reference date (for recency): {REFERENCE_DATE.date()}")

# ─────────────────────────────────────────────────────────────────────────────
# Compute RFM + extended features
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/3] Computing user features…")

# --- All interactions (including rating == 0) ---------------------------------
base = (
    i.groupby("user_id")
    .agg(
        last_interaction=("date", "max"),
        first_interaction=("date", "min"),
        frequency=("recipe_id", "count"),
        unique_recipes=("recipe_id", "nunique"),
    )
    .reset_index()
)

base["recency_days"] = (REFERENCE_DATE - base["last_interaction"]).dt.days
base["days_active"] = (base["last_interaction"] - base["first_interaction"]).dt.days
base["recipes_per_day"] = (
    base["unique_recipes"] / base["days_active"].replace(0, 1)
).round(4)

# --- Explicit ratings only (rating > 0) --------------------------------------
rated = i[i["rating"] > 0].copy()

rating_feats = (
    rated.groupby("user_id")["rating"]
    .agg(
        rating_count="count",
        rating_mean="mean",
        rating_std="std",
        rating_min="min",
        rating_max="max",
    )
    .reset_index()
)

# Fraction of 5-star and low (1–2 star) ratings
pct_5 = (
    rated.groupby("user_id")
    .apply(lambda g: (g["rating"] == 5).mean())
    .reset_index()
    .rename(columns={0: "pct_5star"})
)
pct_low = (
    rated.groupby("user_id")
    .apply(lambda g: (g["rating"] <= 2).mean())
    .reset_index()
    .rename(columns={0: "pct_low_rating"})
)

# --- Merge all ---------------------------------------------------------------
feats = (
    base
    .merge(rating_feats, on="user_id", how="left")
    .merge(pct_5, on="user_id", how="left")
    .merge(pct_low, on="user_id", how="left")
)

# Fill NaN for users who never gave an explicit rating
feats["rating_count"] = feats["rating_count"].fillna(0).astype(int)
feats["rating_mean"] = feats["rating_mean"].fillna(0.0)
feats["rating_std"] = feats["rating_std"].fillna(0.0)
feats["rating_min"] = feats["rating_min"].fillna(0).astype(float)
feats["rating_max"] = feats["rating_max"].fillna(0).astype(float)
feats["pct_5star"] = feats["pct_5star"].fillna(0.0)
feats["pct_low_rating"] = feats["pct_low_rating"].fillna(0.0)

# ─────────────────────────────────────────────────────────────────────────────
# RFM segments (for human-readable bucketing — not used by ML, useful for EDA)
# ─────────────────────────────────────────────────────────────────────────────

def rfm_score(series: pd.Series, n: int = 4, ascending: bool = True) -> pd.Series:
    """Bin a series into n equal-sized quartiles (1=worst, n=best)."""
    labels = list(range(1, n + 1))
    if not ascending:
        labels = labels[::-1]
    try:
        return pd.qcut(series, n, labels=labels, duplicates="drop").astype(float)
    except ValueError:
        return pd.Series(1.0, index=series.index)

feats["R_score"] = rfm_score(feats["recency_days"], ascending=False)  # lower recency = better
feats["F_score"] = rfm_score(feats["frequency"], ascending=True)
feats["M_score"] = rfm_score(feats["rating_mean"].replace(0, np.nan).fillna(0), ascending=True)
feats["RFM_total"] = feats["R_score"] + feats["F_score"] + feats["M_score"]

# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/3] Saving user features…")

# Drop helper date columns (keep only numeric features + user_id)
out_cols = [
    "user_id", "recency_days", "frequency", "unique_recipes",
    "days_active", "recipes_per_day",
    "rating_count", "rating_mean", "rating_std", "rating_min", "rating_max",
    "pct_5star", "pct_low_rating",
    "R_score", "F_score", "M_score", "RFM_total",
]
feats = feats[out_cols]

out_path = PROCESSED / "user_features.parquet"
feats.to_parquet(out_path, index=False)

print(f"  ✓ {len(feats):,} users → {out_path}")

# ─────────────────────────────────────────────────────────────────────────────
# Summary stats
# ─────────────────────────────────────────────────────────────────────────────
print("\nUser feature summary:")
print(feats.drop(columns=["user_id"]).describe().round(2).to_string())

# RFM segment distribution
print("\nRFM total score distribution:")
print(feats["RFM_total"].value_counts().sort_index().to_string())

print("\n✅  04_user_features.py complete.")
