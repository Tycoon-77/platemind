"""
recipes.py — Recipe CRUD and search routes.
"""
from typing import Optional
import httpx
import re
import sqlite3
import json
from fastapi.responses import RedirectResponse
from fastapi import APIRouter, Query, HTTPException
from app import ml_state
from app.ml_state import ROOT

router = APIRouter()

@router.get("/search")
async def search_recipes(
    q: Optional[str] = Query(None, description="Keyword search"),
    cuisine: Optional[str] = Query(None, description="Filter by cuisine"),
    max_time: Optional[int] = Query(None, description="Max total time in minutes"),
):
    """Search recipes using SQLite FTS."""
    conn = sqlite3.connect(ROOT / "data" / "processed" / "recipes.sqlite")
    c = conn.cursor()
    
    query = "SELECT r.recipe_id, r.name, r.minutes, r.description, r.ingredients, r.tags, r.steps FROM recipes r"
    conditions = []
    params = []
    
    if q or cuisine:
        # FTS join
        query += " JOIN recipes_fts f ON r.recipe_id = f.recipe_id"
        match_terms = []
        if q and isinstance(q, str): match_terms.append(q)
        if cuisine and isinstance(cuisine, str): match_terms.append(cuisine)
        
        match_str = " ".join(match_terms)
        conditions.append("recipes_fts MATCH ?")
        params.append(match_str)
        
    if max_time:
        conditions.append("r.minutes <= ?")
        params.append(max_time)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " LIMIT 20"
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        results.append({
            "recipe_id": row[0],
            "name": row[1],
            "minutes": row[2],
            "description": row[3],
            "ingredients": json.loads(row[4]),
            "tags": json.loads(row[5]),
            "steps": json.loads(row[6])
        })

    return {
        "message": "success",
        "params": {"q": q, "cuisine": cuisine, "max_time": max_time},
        "results": results,
    }


_image_cache = {}

@router.get("/{recipe_id}/image")
async def get_recipe_image(recipe_id: int):
    if recipe_id in _image_cache:
        return RedirectResponse(url=_image_cache[recipe_id])

    url = f"https://www.food.com/recipe/test-{recipe_id}"
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200:
                match = re.search(r'<meta name="og:image" content="(.*?)"', resp.text)
                if match:
                    img_url = match.group(1)
                    if "gk-static" not in img_url and "default" not in img_url and "shareGraphic" not in img_url:
                        _image_cache[recipe_id] = img_url
                        return RedirectResponse(url=img_url)
    except Exception as e:
        print(f"Scrape error: {e}")
        
    fallback = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&q=80"
    return RedirectResponse(url=fallback)


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: int):
    """Fetch a single recipe by its integer ID."""
    recipe = ml_state.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found in loaded catalog")
    return recipe
