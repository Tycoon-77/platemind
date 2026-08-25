"""
01_explore.py — Data exploration and cleaning for PlateMind Phase 1.

Reads both raw CSVs, performs cleaning, parses stringified Python lists,
removes outliers, and writes clean Parquet files to data/processed/.

Run:
    python backend/ml/01_explore.py

Outputs:
    data/processed/recipes_clean.parquet
    data/processed/interactions_clean.parquet
    ml/data_dictionary.md  (written by this script)
"""

import ast
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent  # backend/
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

ML_DIR = ROOT / "ml"

print("=" * 60)
print("PHASE 1 — Step 1: Data Exploration & Cleaning")
print("=" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Load raw CSVs
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1/6] Loading raw CSVs…")

recipes_raw = pd.read_csv(RAW / "RAW_recipes.csv")
interactions_raw = pd.read_csv(RAW / "RAW_interactions.csv")

print(f"  recipes_raw:      {recipes_raw.shape[0]:,} rows × {recipes_raw.shape[1]} cols")
print(f"  interactions_raw: {interactions_raw.shape[0]:,} rows × {interactions_raw.shape[1]} cols")

# ─────────────────────────────────────────────────────────────────────────────
# 2.  RECIPES — parsing and cleaning
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/6] Cleaning recipes…")

r = recipes_raw.copy()

# 2a. Parse stringified Python list columns → actual Python lists
#     Columns: ingredients, steps, tags, nutrition
def safe_parse_list(x):
    """Parse a stringified Python list.  Returns [] on failure."""
    if pd.isna(x):
        return []
    try:
        val = ast.literal_eval(x)
        return val if isinstance(val, list) else []
    except Exception:
        return []

r["ingredients"] = r["ingredients"].apply(safe_parse_list)
r["steps"]       = r["steps"].apply(safe_parse_list)
r["tags"]        = r["tags"].apply(safe_parse_list)
r["nutrition"]   = r["nutrition"].apply(safe_parse_list)

# 2b. Expand nutrition vector into named columns
#     Food.com nutrition order (confirmed 7 elements in 100 % of sample):
#     [calories, total_fat_%DV, sugar_%DV, sodium_%DV, protein_%DV,
#      saturated_fat_%DV, carbohydrates_%DV]
NUTR_COLS = ["calories", "total_fat_pdv", "sugar_pdv", "sodium_pdv",
             "protein_pdv", "sat_fat_pdv", "carbs_pdv"]

nutr_df = pd.DataFrame(r["nutrition"].tolist(), columns=NUTR_COLS)
r = pd.concat([r.drop(columns=["nutrition"]), nutr_df], axis=1)

# 2c. Parse submitted date
r["submitted"] = pd.to_datetime(r["submitted"], errors="coerce")

# 2d. Drop name-null row (only 1)
before = len(r)
r = r.dropna(subset=["name"])
print(f"  Dropped {before - len(r)} rows with null name")

# 2e. Clip extreme minutes outliers
#     Keep 0 < minutes <= 1440 (≤ 24 hours). 
#     minutes == 0 → substitute with median (these are likely data entry errors).
MINUTES_CAP = 1440
median_minutes = r.loc[(r["minutes"] > 0) & (r["minutes"] <= MINUTES_CAP), "minutes"].median()
outlier_mask = (r["minutes"] == 0) | (r["minutes"] > MINUTES_CAP)
print(f"  Minutes outliers (0 or >{MINUTES_CAP}) capped to median ({median_minutes}): "
      f"{outlier_mask.sum():,} rows")
r.loc[outlier_mask, "minutes"] = median_minutes

# 2f. Drop duplicates on recipe id (none found in inspection, defensive check)
before = len(r)
r = r.drop_duplicates(subset=["id"])
print(f"  Dropped {before - len(r)} duplicate recipe ids")

# 2g. Rename 'id' → 'recipe_id' to match DB schema; keep 'name' as is
r = r.rename(columns={"id": "recipe_id"})

# 2h. Compute total_minutes convenience column
r["total_minutes"] = r["minutes"]

# 2i. n_ingredients sanity check: compare stored value vs parsed length
mismatch = (r["n_ingredients"] != r["ingredients"].apply(len)).sum()
print(f"  n_ingredients mismatch with parsed list: {mismatch} rows (overriding with parsed len)")
r["n_ingredients"] = r["ingredients"].apply(len)

print(f"  Recipes after cleaning: {len(r):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 3.  INTERACTIONS — cleaning
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/6] Cleaning interactions…")

i = interactions_raw.copy()

# 3a. Parse date
i["date"] = pd.to_datetime(i["date"], errors="coerce")

# 3b. Treat rating == 0 as "no explicit rating" (user reviewed but didn't rate).
#     Keep these rows — they're implicit positive signals — but flag them.
i["has_rating"] = i["rating"] > 0
print(f"  Rating == 0 (implicit view/review only): {(~i['has_rating']).sum():,}")

# 3c. Clip ratings to [1, 5] guard (in case of data errors)
i["rating"] = i["rating"].clip(0, 5)

# 3d. Drop interactions where recipe_id not in cleaned recipes (orphan rows)
valid_recipe_ids = set(r["recipe_id"].values)
before = len(i)
i = i[i["recipe_id"].isin(valid_recipe_ids)]
print(f"  Dropped {before - len(i):,} interactions referencing unknown recipe_ids")

# 3e. Drop duplicate (user_id, recipe_id) pairs — keep the latest interaction
before = len(i)
i = i.sort_values("date").drop_duplicates(subset=["user_id", "recipe_id"], keep="last")
print(f"  Dropped {before - len(i):,} duplicate (user, recipe) pairs — kept latest")

# 3f. Drop null dates (very few, if any)
before = len(i)
i = i.dropna(subset=["date"])
print(f"  Dropped {before - len(i):,} rows with unparseable dates")

print(f"  Interactions after cleaning: {len(i):,}")
print(f"  Unique users: {i['user_id'].nunique():,}")
print(f"  Unique recipes interacted with: {i['recipe_id'].nunique():,}")
print(f"  Date range: {i['date'].min().date()} → {i['date'].max().date()}")

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Filter to recipes that have at least one interaction
#     (keeps data tractable and meaningful for CF models)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/6] Filtering to interacted recipes…")
interacted_ids = set(i["recipe_id"].values)
before = len(r)
r_interacted = r[r["recipe_id"].isin(interacted_ids)].copy()
print(f"  Recipes with ≥1 interaction: {len(r_interacted):,} "
      f"(dropped {before - len(r_interacted):,} un-interacted)")
# We keep the full r for the DB load script; r_interacted is for ML.

# ─────────────────────────────────────────────────────────────────────────────
# 5.  Save cleaned Parquet files
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5/6] Saving cleaned Parquet files…")

r.to_parquet(PROCESSED / "recipes_clean.parquet", index=False)
i.to_parquet(PROCESSED / "interactions_clean.parquet", index=False)
r_interacted.to_parquet(PROCESSED / "recipes_interacted.parquet", index=False)

print(f"  ✓ data/processed/recipes_clean.parquet          ({len(r):,} rows)")
print(f"  ✓ data/processed/interactions_clean.parquet     ({len(i):,} rows)")
print(f"  ✓ data/processed/recipes_interacted.parquet     ({len(r_interacted):,} rows)")

# ─────────────────────────────────────────────────────────────────────────────
# 6.  Print summary statistics for the data dictionary
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6/6] Summary stats (for data_dictionary.md)…")
print("\nRecipe minutes distribution (after capping):")
print(r["minutes"].describe().to_string())
print("\nRecipe n_ingredients distribution:")
print(r["n_ingredients"].describe().to_string())
print("\nRecipe n_steps distribution:")
print(r["n_steps"].describe().to_string())
print("\nRecipe calories distribution:")
print(r["calories"].describe().to_string())
print("\nInteraction rating distribution (excl. 0):")
print(i[i["rating"] > 0]["rating"].value_counts().sort_index().to_string())

print("\n✅  01_explore.py complete.")
