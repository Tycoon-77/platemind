import json
import math
import pandas as pd
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"

import importlib.util

try:
    spec = importlib.util.spec_from_file_location("normalize_ingredients", ROOT / "ml" / "02_normalize_ingredients.py")
    norm_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(norm_module)
    normalize_many = norm_module.normalize_many
except Exception as e:
    print(f"Failed to import 02_normalize_ingredients: {e}")
    # Fallback dummy for type checking
    normalize_many = lambda x: x

class PantryMatcher:
    def __init__(self, idf_dict: Dict[str, float] = None):
        """
        idf_dict: Dictionary mapping normalized ingredient name to its IDF score.
                  If None, it must be loaded or fit before scoring.
        """
        self.idf_dict = idf_dict or {}
        # Default IDF for unknown ingredients (log(N / 1) ≈ log(230000) ≈ 12.3)
        self.default_idf = 12.3

    def get_idf(self, ingredient: str) -> float:
        return self.idf_dict.get(ingredient, self.default_idf)

    def score(self, pantry: List[str], recipe_ingredients: List[str]) -> float:
        """
        Calculates a weighted overlap score between user's pantry and a recipe.
        Returns a float between 0.0 and 1.0.
        """
        if not recipe_ingredients:
            return 0.0

        pantry_norm = set(normalize_many(pantry))
        recipe_norm = set(normalize_many(recipe_ingredients))

        if not recipe_norm:
            return 0.0

        intersection = pantry_norm.intersection(recipe_norm)

        # Calculate TF-IDF weighted overlap
        # TF is binary (1 if present in recipe, 0 otherwise)
        intersection_weight = sum(self.get_idf(ing) for ing in intersection)
        recipe_total_weight = sum(self.get_idf(ing) for ing in recipe_norm)

        if recipe_total_weight == 0:
            return 0.0

        return intersection_weight / recipe_total_weight

    def fit(self, recipes_df: pd.DataFrame, save_path: Path = None):
        """
        Computes IDF from a DataFrame containing an 'ingredients' column 
        (list of raw ingredient strings).
        """
        print("Fitting PantryMatcher IDF...")
        import ast
        import numpy as np
        
        doc_freq = {}
        total_docs = len(recipes_df)
        
        for ing_col in recipes_df['ingredients']:
            if isinstance(ing_col, str):
                try: ing_col = ast.literal_eval(ing_col)
                except: ing_col = []
            elif isinstance(ing_col, np.ndarray):
                ing_col = ing_col.tolist()
                
            if not isinstance(ing_col, list):
                continue
                
            # Normalize recipe ingredients
            norm_ings = set(normalize_many(ing_col))
            for ing in norm_ings:
                doc_freq[ing] = doc_freq.get(ing, 0) + 1
                
        # Calculate IDF
        self.idf_dict = {
            ing: math.log(total_docs / (1 + count)) 
            for ing, count in doc_freq.items()
        }
        
        # Determine max IDF for unknown words
        self.default_idf = math.log(total_docs / 1.0)
        
        if save_path:
            with open(save_path, "w") as f:
                json.dump({"default_idf": self.default_idf, "idf_dict": self.idf_dict}, f)
            print(f"Saved IDF dict to {save_path}")

    @classmethod
    def load(cls, load_path: Path):
        with open(load_path, "r") as f:
            data = json.load(f)
        matcher = cls(idf_dict=data.get("idf_dict", {}))
        matcher.default_idf = data.get("default_idf", 12.3)
        return matcher

if __name__ == "__main__":
    print("============================================================")
    print("PHASE 2 — Step 8: Pantry Matcher Setup")
    print("============================================================")
    df = pd.read_parquet(PROCESSED / "recipes_clean.parquet")
    matcher = PantryMatcher()
    
    # We will fit on 50,000 recipes for speed if doing this interactively,
    # but let's just fit on all since it's just Python strings and sets.
    matcher.fit(df, save_path=MODELS_DIR / "pantry_idf.json")
    
    # Quick test
    test_pantry = ["chicken breast", "salt", "black pepper", "olive oil", "garlic"]
    test_recipe_1 = ["chicken breast", "salt", "pepper", "olive oil"]
    test_recipe_2 = ["salmon", "lemon", "salt", "pepper"]
    test_recipe_3 = ["salt", "water", "garlic"] # mostly cheap ingredients
    test_recipe_4 = ["saffron", "truffle oil", "chicken breast"] # rare ingredients missing

    print(f"\nPantry: {test_pantry}")
    print(f"Recipe 1 {test_recipe_1} -> Score: {matcher.score(test_pantry, test_recipe_1):.3f}")
    print(f"Recipe 2 {test_recipe_2} -> Score: {matcher.score(test_pantry, test_recipe_2):.3f}")
    print(f"Recipe 3 {test_recipe_3} -> Score: {matcher.score(test_pantry, test_recipe_3):.3f}")
    print(f"Recipe 4 {test_recipe_4} -> Score: {matcher.score(test_pantry, test_recipe_4):.3f}")
    
    print("✅  08_pantry_matcher.py complete.")
