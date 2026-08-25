import ast
import gc
import pandas as pd
import numpy as np
import torch
from pathlib import Path
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

print("============================================================")
print("PHASE 2 — Step 7: Recipe Embeddings")
print("============================================================")

print("[1/3] Loading recipes…")
df = pd.read_parquet(PROCESSED / "recipes_clean.parquet")
train_int = pd.read_parquet(PROCESSED / "train_interactions.parquet")
test_int = pd.read_parquet(PROCESSED / "test_interactions.parquet")

# We only need a subset for the hybrid ranker demo.
# Let's pick 500 users, get all their interacted items, plus 5000 random warm items.
np.random.seed(42)
sample_users = np.random.choice(test_int['user_id'].unique(), size=500, replace=False)
user_items = set(train_int[train_int['user_id'].isin(sample_users)]['recipe_id'])
user_items.update(test_int[test_int['user_id'].isin(sample_users)]['recipe_id'])

warm_items = train_int['recipe_id'].unique()
random_items = np.random.choice(warm_items, size=5000, replace=False)

items_to_embed = user_items.union(set(random_items))
print(f"  Filtering to {len(items_to_embed)} items for rapid Phase 2 pipeline evaluation...")

df = df[df['recipe_id'].isin(items_to_embed)].copy()

def prep_text(row):
    name = str(row['name'])
    ing = row['ingredients']
    if isinstance(ing, str):
        try: ing = ast.literal_eval(ing)
        except: ing = []
    elif isinstance(ing, np.ndarray):
        ing = ing.tolist()
    ing_text = ", ".join(ing) if isinstance(ing, list) else ""
    
    steps = row['steps']
    if isinstance(steps, str):
        try: steps = ast.literal_eval(steps)
        except: steps = []
    elif isinstance(steps, np.ndarray):
        steps = steps.tolist()
    steps_text = " ".join(steps) if isinstance(steps, list) else ""
    
    return f"Recipe: {name}. Ingredients: {ing_text}. Instructions: {steps_text}."

print("[2/3] Preparing text for embedding…")
texts = df.apply(prep_text, axis=1).tolist()
recipe_ids = df['recipe_id'].tolist()

print("[3/3] Generating embeddings (all-MiniLM-L6-v2)…")
model = SentenceTransformer('all-MiniLM-L6-v2')
model.to("cpu")

embeddings_list = []
batch_size = 1000

for i in range(0, len(texts), batch_size):
    batch_texts = texts[i:i+batch_size]
    emb = model.encode(batch_texts, batch_size=128, show_progress_bar=True, convert_to_numpy=True)
    embeddings_list.extend(emb.tolist())
    gc.collect()

print("  Saving to embeddings.parquet…")
emb_df = pd.DataFrame({
    "recipe_id": recipe_ids,
    "embedding": embeddings_list
})
emb_df.to_parquet(PROCESSED / "embeddings.parquet", index=False)
print("✅  07_embeddings.py complete.")
