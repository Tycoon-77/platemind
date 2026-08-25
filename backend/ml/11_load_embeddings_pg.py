"""
11_load_embeddings_pg.py — Bulk load recipe embeddings into Supabase/pgvector.
Commits per batch so progress is visible and restartable.
"""
import os, ast
import numpy as np
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("=" * 60)
print("PHASE 2/3 — Step 11: Load Embeddings into pgvector")
print("=" * 60)

PROCESSED = ROOT / "data" / "processed"
print("[1/4] Loading parquet files...")
emb_df = pd.read_parquet(PROCESSED / "embeddings.parquet")
rcp_df = pd.read_parquet(PROCESSED / "recipes_clean.parquet")
rcp_df = rcp_df[rcp_df["recipe_id"].isin(emb_df["recipe_id"])]
print(f"       {len(emb_df)} embeddings, {len(rcp_df)} recipes with embeddings")

print("[2/4] Merging...")
def to_list(val):
    if isinstance(val, (list, np.ndarray)): return list(val)
    if isinstance(val, str):
        try: return ast.literal_eval(val)
        except: return []
    return []

merged = rcp_df.set_index("recipe_id").join(
    emb_df.set_index("recipe_id")[["embedding"]], how="inner"
).reset_index()
merged["tags"] = merged["tags"].apply(to_list)
merged["ingredients"] = merged["ingredients"].apply(to_list)

print("[3/4] Connecting...")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

print("[4/4] Upserting rows (per-batch commits)...")
BATCH = 200
total = len(merged)
inserted = 0

for start in range(0, total, BATCH):
    batch = merged.iloc[start : start + BATCH]
    rows = []
    for _, row in batch.iterrows():
        emb_list = row["embedding"]
        if isinstance(emb_list, np.ndarray): emb_list = emb_list.tolist()
        emb_str = "[" + ",".join(f"{v:.6f}" for v in emb_list) + "]"
        rows.append({
            "recipe_id": int(row["recipe_id"]),
            "name": str(row.get("name") or ""),
            "minutes": int(row.get("minutes") or 0),
            "tags": list(row["tags"]),
            "ingredients": list(row["ingredients"]),
            "embedding": emb_str,
        })

    # Commit per batch — so progress is durable and visible in Supabase
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO recipes (recipe_id, name, minutes, tags, ingredients, embedding)
            VALUES (:recipe_id, :name, :minutes, :tags, :ingredients, CAST(:embedding AS vector))
            ON CONFLICT (recipe_id) DO UPDATE SET
                name = EXCLUDED.name,
                minutes = EXCLUDED.minutes,
                tags = EXCLUDED.tags,
                ingredients = EXCLUDED.ingredients,
                embedding = EXCLUDED.embedding
        """), rows)

    inserted += len(batch)
    print(f"  {inserted}/{total} ({100*inserted//total}%) committed", flush=True)

print(f"\nAll {inserted} rows upserted.")

# Verification
with engine.connect() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM recipes WHERE embedding IS NOT NULL")).scalar()
    sample = conn.execute(text("""
        SELECT recipe_id, name, array_length(ingredients, 1) AS n_ings
        FROM recipes WHERE embedding IS NOT NULL LIMIT 3
    """)).fetchall()

print(f"\n✅ Verification: {count} rows have embedding in Supabase")
for row in sample:
    print(f"   recipe_id={row[0]}  name={row[1]!r}  n_ingredients={row[2]}")

print("\n11_load_embeddings_pg.py complete!")
