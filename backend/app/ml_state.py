import numpy as np
import pickle
import json
import sqlite3
from pathlib import Path
import lightgbm as lgb
import importlib.util
import sys

class MatrixFactorization:
    def __init__(self, factors: int = 64, iterations: int = 30,
                 regularization: float = 0.05, alpha: float = 40.0):
        pass
sys.modules['__main__'].MatrixFactorization = MatrixFactorization

ROOT = Path(__file__).resolve().parent.parent

# Load pantry matcher class
pm_spec = importlib.util.spec_from_file_location("pantry_matcher", ROOT / "ml" / "08_pantry_matcher.py")
pm_mod = importlib.util.module_from_spec(pm_spec)
pm_spec.loader.exec_module(pm_mod)
PantryMatcher = pm_mod.PantryMatcher

# Load normalize_many
norm_spec = importlib.util.spec_from_file_location("normalize_ingredients", ROOT / "ml" / "02_normalize_ingredients.py")
norm_mod = importlib.util.module_from_spec(norm_spec)
norm_spec.loader.exec_module(norm_mod)
normalize_many = norm_mod.normalize_many

# State variables
emb_dict = {}
recipe_ings_norm = {}
recipe_tags_set = {}
mf_model = None
hybrid_model = None
matcher = None

# We no longer keep recipes_dict in RAM. We fetch from SQLite.
def get_recipe(rid: int) -> dict:
    conn = sqlite3.connect(ROOT / "data" / "processed" / "recipes.sqlite")
    c = conn.cursor()
    c.execute("SELECT name, minutes, description, ingredients, tags, steps FROM recipes WHERE recipe_id=?", (rid,))
    row = c.fetchone()
    conn.close()
    if not row: return None
    return {
        "recipe_id": rid,
        "name": row[0],
        "minutes": row[1],
        "description": row[2],
        "ingredients": json.loads(row[3]),
        "tags": json.loads(row[4]),
        "steps": json.loads(row[5])
    }

def init_ml_state():
    global emb_dict, recipe_ings_norm, recipe_tags_set
    global mf_model, hybrid_model, matcher

    print("Initializing ML State for FastAPI (Optimized SQLite Mode)...")
    MODELS_DIR = ROOT / "models"
    PROCESSED = ROOT / "data" / "processed"

    print("  Loading models...")
    with open(MODELS_DIR / "mf_model.pkl", "rb") as f: mf_model = pickle.load(f)
    with open(MODELS_DIR / "hybrid_lgb.pkl", "rb") as f: hybrid_model = pickle.load(f)
    matcher = PantryMatcher.load(MODELS_DIR / "pantry_idf.json")
    
    print("  Loading embeddings (Pickle)...")
    try:
        with open(MODELS_DIR / "emb_dict.pkl", "rb") as f:
            emb_dict.update(pickle.load(f))
    except Exception as e:
        print(f"Warning: could not load emb_dict.pkl: {e}")

    print("  Loading lightweight ML indices from SQLite...")
    conn = sqlite3.connect(PROCESSED / "recipes.sqlite")
    c = conn.cursor()
    c.execute("SELECT recipe_id, ingredients_norm, tags FROM recipes")
    for rid, ing_norm, tags in c.fetchall():
        recipe_ings_norm[rid] = json.loads(ing_norm)
        recipe_tags_set[rid] = set(json.loads(tags))
    conn.close()

    print(f"ML State Initialized! (Loaded {len(recipe_ings_norm)} indices)")

