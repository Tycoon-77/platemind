"""
03_load_db.py — Load cleaned data into a local SQLite database.

⚠️  DATABASE CHOICE — SQLITE FOR NOW:
    This script uses SQLite (via Python's built-in sqlite3) rather than
    PostgreSQL/Supabase because:
      a) No Supabase project is yet configured in Phase 0.
      b) SQLite requires zero setup and makes Phase 1 fully self-contained.

    Migration to Postgres:
      - In Phase 4, set DATABASE_URL in backend/.env and rerun with
        the Postgres adapter (asyncpg + SQLAlchemy).
      - The table schemas below match the PRD exactly so no ETL rework
        is needed.
      - pgvector (recipes.embedding) is omitted here; it is populated in
        Phase 2 after sentence-transformers embeddings are generated.

Output:
    data/processed/platemind.db  — SQLite database

Tables populated:
    recipes            (id, name, description, minutes, n_steps, n_ingredients,
                        submitted, calories, protein_pdv, ...)
    ingredients        (id, name, normalized_name)
    recipe_ingredients (recipe_id, ingredient_id, position)
    user_interactions  (id, user_id, recipe_id, rating, date, has_rating)

Run:
    python backend/ml/03_load_db.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
DB_PATH = PROCESSED / "platemind.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create tables matching the PRD schema (SQLite flavour)."""
    conn.executescript(
        """
        -- Recipes ----------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS recipes (
            id              INTEGER PRIMARY KEY,
            name            TEXT    NOT NULL,
            description     TEXT,
            minutes         INTEGER,
            n_steps         INTEGER,
            n_ingredients   INTEGER,
            submitted       TEXT,
            calories        REAL,
            total_fat_pdv   REAL,
            sugar_pdv       REAL,
            sodium_pdv      REAL,
            protein_pdv     REAL,
            sat_fat_pdv     REAL,
            carbs_pdv       REAL
        );

        -- Ingredients ------------------------------------------------------------
        CREATE TABLE IF NOT EXISTS ingredients (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT UNIQUE NOT NULL,
            normalized_name TEXT NOT NULL
        );

        -- Recipe × Ingredient join -----------------------------------------------
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            recipe_id       INTEGER NOT NULL REFERENCES recipes(id),
            ingredient_id   INTEGER NOT NULL REFERENCES ingredients(id),
            position        INTEGER,
            PRIMARY KEY (recipe_id, ingredient_id)
        );

        -- User interactions -------------------------------------------------------
        CREATE TABLE IF NOT EXISTS user_interactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            recipe_id       INTEGER NOT NULL REFERENCES recipes(id),
            rating          INTEGER,
            has_rating      INTEGER,          -- 0/1 boolean
            date            TEXT,
            review_snippet  TEXT              -- first 500 chars for context
        );

        -- Indexes -----------------------------------------------------------------
        CREATE INDEX IF NOT EXISTS idx_ri_recipe  ON recipe_ingredients(recipe_id);
        CREATE INDEX IF NOT EXISTS idx_ri_ingr    ON recipe_ingredients(ingredient_id);
        CREATE INDEX IF NOT EXISTS idx_ui_user    ON user_interactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_ui_recipe  ON user_interactions(recipe_id);
        """
    )
    conn.commit()


def load_recipes(conn: sqlite3.Connection, recipes: pd.DataFrame) -> None:
    print("  Loading recipes…")
    cols = [
        "recipe_id", "name", "description", "minutes", "n_steps", "n_ingredients",
        "submitted", "calories", "total_fat_pdv", "sugar_pdv", "sodium_pdv",
        "protein_pdv", "sat_fat_pdv", "carbs_pdv",
    ]
    df = recipes[cols].copy()
    df["submitted"] = df["submitted"].astype(str)
    # Rename recipe_id → id for DB
    df = df.rename(columns={"recipe_id": "id"})
    df.to_sql("recipes", conn, if_exists="replace", index=False)
    print(f"    ✓ {len(df):,} recipes")


def load_ingredients_and_bridge(
    conn: sqlite3.Connection,
    recipes: pd.DataFrame,
    ing_norm: pd.DataFrame,
) -> None:
    """
    Build the ingredients table and recipe_ingredients bridge table.
    """
    print("  Building ingredient vocabulary…")

    # Map raw_name → normalized_name
    raw_to_norm = dict(zip(ing_norm["raw_name"], ing_norm["normalized_name"]))

    # Collect all (recipe_id, raw_name, position) triples
    rows = []
    for _, row in recipes.iterrows():
        for pos, raw in enumerate(row["ingredients"]):
            rows.append((int(row["recipe_id"]), str(raw), pos))

    bridge_raw = pd.DataFrame(rows, columns=["recipe_id", "raw_name", "position"])

    # Unique ingredients by raw name → assign integer IDs
    unique_raw = bridge_raw[["raw_name"]].drop_duplicates().reset_index(drop=True)
    unique_raw["normalized_name"] = unique_raw["raw_name"].map(raw_to_norm).fillna(
        unique_raw["raw_name"]
    )
    unique_raw.index = unique_raw.index + 1  # 1-based IDs
    unique_raw.index.name = "id"
    unique_raw = unique_raw.reset_index()

    unique_raw.to_sql("ingredients", conn, if_exists="replace", index=False)
    print(f"    ✓ {len(unique_raw):,} unique ingredients")

    # Build bridge
    raw_to_id = dict(zip(unique_raw["raw_name"], unique_raw["id"]))
    bridge_raw["ingredient_id"] = bridge_raw["raw_name"].map(raw_to_id)
    bridge = bridge_raw[["recipe_id", "ingredient_id", "position"]].dropna()
    bridge["ingredient_id"] = bridge["ingredient_id"].astype(int)
    bridge.to_sql("recipe_ingredients", conn, if_exists="replace", index=False)
    print(f"    ✓ {len(bridge):,} recipe×ingredient links")


def load_interactions(conn: sqlite3.Connection, interactions: pd.DataFrame) -> None:
    print("  Loading interactions…")

    # Only keep interactions whose recipe_id is in the DB
    valid_ids = pd.read_sql("SELECT id FROM recipes", conn)["id"].tolist()
    df = interactions[interactions["recipe_id"].isin(valid_ids)].copy()

    df["date"] = df["date"].astype(str)
    df["has_rating"] = df["has_rating"].astype(int)

    # Truncate review to 500 chars to keep DB size reasonable
    if "review" in df.columns:
        df["review_snippet"] = df["review"].fillna("").str[:500]
    else:
        df["review_snippet"] = ""

    out = df[["user_id", "recipe_id", "rating", "has_rating", "date", "review_snippet"]]
    out.to_sql("user_interactions", conn, if_exists="replace", index=False)
    print(f"    ✓ {len(out):,} interactions")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 — Step 3: Load to SQLite")
    print("=" * 60)
    print(f"\n  DB path: {DB_PATH}")
    print("\n  ⚠️  Using SQLite (not Postgres).")
    print("     Migrate to Postgres in Phase 4 by swapping the connection.\n")

    # Check dependencies
    for fname in ["recipes_clean.parquet", "interactions_clean.parquet",
                  "ingredients_normalized.parquet"]:
        if not (PROCESSED / fname).exists():
            print(f"ERROR: {fname} missing — run 01_explore.py and 02_normalize_ingredients.py first")
            sys.exit(1)

    recipes = pd.read_parquet(PROCESSED / "recipes_clean.parquet")
    interactions = pd.read_parquet(PROCESSED / "interactions_clean.parquet")
    ing_norm = pd.read_parquet(PROCESSED / "ingredients_normalized.parquet")

    print(f"  Loaded {len(recipes):,} recipes, {len(interactions):,} interactions, "
          f"{len(ing_norm):,} ingredient mappings")

    conn = get_conn()
    try:
        create_schema(conn)
        load_recipes(conn, recipes)
        load_ingredients_and_bridge(conn, recipes, ing_norm)
        load_interactions(conn, interactions)

        # Verification queries
        print("\n  Verification:")
        for table in ["recipes", "ingredients", "recipe_ingredients", "user_interactions"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"    {table}: {count:,} rows")

        conn.commit()
    finally:
        conn.close()

    print(f"\n✅  03_load_db.py complete → {DB_PATH}")
