# PlateMind — Data Dictionary

## Source Dataset

**Food.com Recipes and Interactions** (Kaggle, 2019)
- `RAW_recipes.csv` — ~267,782 rows × 12 columns
- `RAW_interactions.csv` — ~1,327,042 rows × 5 columns

Real user interaction data (not synthetic), spanning 2000–2018.

---

## RAW_recipes.csv

| Column | Raw type | Notes |
|---|---|---|
| `name` | string | Recipe name. 1 null row (dropped). |
| `id` | int64 | Source recipe ID. No duplicates. Used as primary key. |
| `minutes` | int64 | Total time in minutes. Highly skewed: median 38, max 201,610 (!). Values 0 or >1440 treated as outliers and replaced with the median. |
| `contributor_id` | int64 | Food.com user ID of the recipe author. Not used in MVP. |
| `submitted` | string→date | Date recipe was submitted. Range: 1999-08-06 → 2018-11-12. Parsed to `datetime`. |
| `tags` | string→list[str] | Stringified Python list of Food.com taxonomy tags (e.g. `['60-minutes-or-less', 'vegetarian']`). Parsed with `ast.literal_eval`. Not stored in DB, but used for dietary-tag extraction in Phase 2. |
| `nutrition` | string→list[float] | Stringified Python list of **exactly 7** floats. Vector order (confirmed): `[calories, total_fat_%DV, sugar_%DV, sodium_%DV, protein_%DV, saturated_fat_%DV, carbohydrates_%DV]`. Values are % Daily Value except calories (kcal). |
| `n_steps` | int64 | Number of cooking steps. Range: 0–108, median 9. |
| `steps` | string→list[str] | Stringified Python list of step strings. Parsed with `ast.literal_eval`. |
| `description` | string | Free-text description. 230 nulls in the first 10k rows (~2.3%); kept as null in DB. |
| `ingredients` | string→list[str] | Stringified Python list of ingredient name strings. **Already clean lower-case strings** from Food.com. No unit/quantity information — just names (e.g. `['eggs', 'butter', 'sugar']`). |
| `n_ingredients` | int64 | Stored count; recomputed from parsed list length to fix mismatches. Range: 1–43, median 9. |

### Nutrition vector mapping

| Index | Column name | Unit |
|---|---|---|
| 0 | `calories` | kcal |
| 1 | `total_fat_pdv` | % Daily Value |
| 2 | `sugar_pdv` | % Daily Value |
| 3 | `sodium_pdv` | % Daily Value |
| 4 | `protein_pdv` | % Daily Value |
| 5 | `sat_fat_pdv` | % Daily Value |
| 6 | `carbs_pdv` | % Daily Value |

### Outlier handling — `minutes`

| Condition | Count | Treatment |
|---|---|---|
| `minutes == 0` | ~44 in first 10k | Replaced with column median |
| `minutes > 1440` (>1 day) | ~108 in first 10k | Replaced with column median |
| Extreme examples | "14-day coleslaw" (20,175 min), "marijuana vinegar" (20,160 min) | Capped |

---

## RAW_interactions.csv

| Column | Raw type | Notes |
|---|---|---|
| `user_id` | int64 | Food.com user ID. |
| `recipe_id` | int64 | Matches `id` in RAW_recipes.csv. |
| `date` | string→date | Date of interaction. Format: YYYY-MM-DD. Range: 2000-11-20 → 2018-12-05. |
| `rating` | int64 | 1–5 star rating, OR **0** = user left a review without a star rating. Treat 0 as implicit engagement signal, not as a 0/5 rating. |
| `review` | string | Free-text review. 2 nulls in first 10k rows. Truncated to 500 chars in DB to control size. |

### Rating distribution (from 10k sample)

| Rating | Count | Interpretation |
|---|---|---|
| 0 | 520 | Review only, no star rating — implicit positive signal |
| 1 | 110 | Explicit dislike |
| 2 | 119 | Below average |
| 3 | 377 | Average |
| 4 | 1,650 | Good |
| 5 | 7,224 | Excellent — strong skew toward 5-star |

> **Note**: The 5-star skew is typical of voluntary review datasets (selection bias).  Users who liked a recipe enough to return and rate it tend to give 5 stars.  Matrix factorization via ALS treats ratings as confidence weights (not raw values), which is more robust to this skew than explicit feedback models.

---

## Cleaned / Processed Files

| File | Rows | Description |
|---|---|---|
| `data/processed/recipes_clean.parquet` | ~267,781 | Full recipe table with parsed columns and expanded nutrition |
| `data/processed/recipes_interacted.parquet` | subset | Recipes that have ≥1 user interaction (used for ML training) |
| `data/processed/interactions_clean.parquet` | ~1.13M | Cleaned interactions; deduplicated to last per (user, recipe) |
| `data/processed/ingredients_normalized.parquet` | ~10k unique | raw_name → normalized_name mapping (all unique ingredient strings) |
| `data/processed/user_features.parquet` | ~226k users | RFM + extended per-user features |
| `data/processed/train_interactions.parquet` | ~warm set | CF training split |
| `data/processed/test_interactions.parquet` | ~warm set | CF leave-last-out test split |
| `data/processed/platemind.db` | — | SQLite DB with recipes, ingredients, recipe_ingredients, user_interactions |

---

## Key Design Decisions

### `ingredients` column
- Ingredients are already name-only strings (no quantities) in the source data.
- They are stored as proper Python lists after `ast.literal_eval()` parsing.
- The normalization pipeline (`02_normalize_ingredients.py`) maps each raw string to a canonical `normalized_name` for pantry matching.

### `rating == 0`
- Not treated as a rating of 0/5.
- Kept as rows with `has_rating = False`.
- Used as implicit positive signal in ALS (the user engaged enough to write a review).
- Excluded from explicit CF training (User-CF, Item-CF) to avoid artificially depressing scores.

### Interaction deduplication
- When a user rated the same recipe multiple times, only the **latest** interaction is kept.
- This handles cases where users updated their review.

### Minutes capping
- Recipes with `minutes == 0` or `minutes > 1440` are floored/capped at the column median (~38 min).
- These extremes are almost always data-entry errors or multi-day processes (fermentation, etc.).
- Total minutes are stored as-is for the detail page; the capped value is used for ranking and filtering only.

---

*Generated by `01_explore.py` and manually extended — update if the cleaning logic changes.*

---

## Phase 2 Scoping Decision — Embedding Corpus Cap

**Decision**: Embeddings were generated for a capped subset of ~13,352 recipes, not the full 231k catalog.

**Rationale**: Generating `all-MiniLM-L6-v2` embeddings for the full 231k recipe corpus on CPU would take 4–6 hours and ~24 GB of RAM. The cap covers the "warm" set (recipes with ≥3 user interactions) plus a random sample to reach ~13k total — this accounts for the recipes most likely to be recommended, ensuring coverage is high for active items.

**Impact**: Cold recipes (never interacted with) are not searchable via pgvector. They remain accessible via the full-text keyword search endpoint. This cap will be lifted in a future phase if GPU compute is provisioned.

**Where applied**: `07_embeddings.py` selects the warm corpus, then pads to ~13k with a random sample if needed.

**Supabase pgvector**: Only these 13k recipes are uploaded to the `recipes` table's `embedding` column (via `11_load_embeddings_pg.py`). The remainder of the table is empty and not yet populated.

