import pandas as pd
import numpy as np
import pickle
import ast
from pathlib import Path
import lightgbm as lgb

import sys
class MatrixFactorization:
    def __init__(self, factors: int = 64, iterations: int = 30,
                 regularization: float = 0.05, alpha: float = 40.0):
        pass
sys.modules['__main__'].MatrixFactorization = MatrixFactorization

import importlib.util
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
recipes_dict = {}
emb_dict = {}
recipe_ings_norm = {}
recipe_tags_set = {}
mf_model = None
hybrid_model = None
matcher = None

def init_ml_state():
    global recipes_dict, emb_dict, recipe_ings_norm, recipe_tags_set
    global mf_model, hybrid_model, matcher

    print("Initializing ML State for FastAPI...")
    MODELS_DIR = ROOT / "models"
    PROCESSED = ROOT / "data" / "processed"

    print("  Loading models...")
    with open(MODELS_DIR / "mf_model.pkl", "rb") as f:
        mf_model = pickle.load(f)
    
    with open(MODELS_DIR / "hybrid_lgb.pkl", "rb") as f:
        hybrid_model = pickle.load(f)
        
    matcher = PantryMatcher.load(MODELS_DIR / "pantry_idf.json")
    
    print("  Loading data...")
    try:
        embeddings_df = pd.read_parquet(PROCESSED / "embeddings.parquet")
        for _, row in embeddings_df.iterrows():
            emb_dict[row['recipe_id']] = np.array(row['embedding'])
    except Exception as e:
        print(f"Warning: could not load embeddings.parquet: {e}")

    recipes_df = pd.read_parquet(PROCESSED / "recipes_clean.parquet")
    
    # Optional: subset recipes_df to only those we have embeddings for, to save RAM
    if emb_dict:
        recipes_df = recipes_df[recipes_df['recipe_id'].isin(emb_dict.keys())]

    print(f"  Parsing {len(recipes_df)} recipes into memory...")
    for row in recipes_df.itertuples():
        rid = row.recipe_id
        
        # Raw Dict
        r_dict = {
            "recipe_id": rid,
            "name": row.name,
            "minutes": row.minutes,
            "description": row.description,
            "ingredients": row.ingredients,
            "tags": row.tags,
            "steps": row.steps
        }
        
        # Clean ingredients
        ing = row.ingredients
        if isinstance(ing, str):
            try: ing = ast.literal_eval(ing)
            except: ing = []
        elif isinstance(ing, np.ndarray): ing = ing.tolist()
        if not isinstance(ing, list): ing = []
        r_dict['ingredients'] = ing
        recipe_ings_norm[rid] = normalize_many(ing)
        
        # Clean tags
        tag = row.tags
        if isinstance(tag, str):
            try: tag = ast.literal_eval(tag)
            except: tag = []
        elif isinstance(tag, np.ndarray): tag = tag.tolist()
        if not isinstance(tag, list): tag = []
        r_dict['tags'] = tag
        recipe_tags_set[rid] = set(tag)
        
        # Clean steps
        steps = row.steps
        if isinstance(steps, str):
            try: steps = ast.literal_eval(steps)
            except: steps = []
        elif isinstance(steps, np.ndarray): steps = steps.tolist()
        if not isinstance(steps, list): steps = []
        r_dict['steps'] = steps

        recipes_dict[rid] = r_dict

    print("ML State Initialized!")
