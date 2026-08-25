import pandas as pd
import ast
import numpy as np
from pathlib import Path
import importlib.util

ROOT = Path('backend').resolve()
PROCESSED = ROOT / 'data' / 'processed'

train_int = pd.read_parquet(PROCESSED / 'train_interactions.parquet')
test_int = pd.read_parquet(PROCESSED / 'test_interactions.parquet')
recipes_df = pd.read_parquet(PROCESSED / 'recipes_clean.parquet')

spec = importlib.util.spec_from_file_location("normalize_ingredients", ROOT / "ml" / "02_normalize_ingredients.py")
norm_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(norm_mod)
normalize_many = norm_mod.normalize_many

recipe_ings = {}
for row in recipes_df[['recipe_id', 'ingredients']].itertuples():
    ing = row.ingredients
    if isinstance(ing, str):
        try: ing = ast.literal_eval(ing)
        except: ing = []
    elif isinstance(ing, np.ndarray): ing = ing.tolist()
    if isinstance(ing, list): recipe_ings[row.recipe_id] = set(normalize_many(ing))
    else: recipe_ings[row.recipe_id] = set()

test_users = test_int['user_id'].unique()[:500]
leaks = 0
for uid in test_users:
    user_train = train_int[train_int['user_id'] == uid]['recipe_id']
    train_ings = set()
    for rid in user_train:
        train_ings.update(recipe_ings.get(rid, set()))
    
    test_recipe = test_int[test_int['user_id'] == uid]['recipe_id'].iloc[0]
    test_ings = recipe_ings.get(test_recipe, set())
    
    if len(train_ings.intersection(test_ings)) > 0:
        leaks += 1
        
print(f'Leakage check: {leaks} users out of {len(test_users)} have overlapping ingredients.')
