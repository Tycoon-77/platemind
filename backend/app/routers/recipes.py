"""
recipes.py — Recipe CRUD and search routes.

GET  /recipes/{id}               — Fetch a single recipe by its ID.
GET  /recipes/search             — Search recipes by keyword, cuisine, max prep+cook time.
     Query params: q, cuisine, max_time

Phase 0: stubs returning placeholder responses.
Phase 4: wire to Postgres via async SQLAlchemy / Supabase client.
"""
from typing import Optional
import httpx
import re
from fastapi.responses import RedirectResponse
from fastapi import APIRouter, Query, HTTPException
from app import ml_state

router = APIRouter()

@router.get("/search")
async def search_recipes(
    q: Optional[str] = Query(None, description="Keyword search"),
    cuisine: Optional[str] = Query(None, description="Filter by cuisine"),
    max_time: Optional[int] = Query(None, description="Max total time in minutes"),
):
    """Search recipes by keyword, cuisine, and/or max total time."""
    results = []
    
    # In-memory search fallback (Phase 4 will move this to Postgres FTS)
    q_lower = q.lower() if q else None
    cuisine_lower = cuisine.lower() if cuisine else None
    
    for rid, recipe in ml_state.recipes_dict.items():
        if max_time and recipe.get("minutes", 9999) > max_time:
            continue
            
        if q_lower:
            name = recipe.get("name") or ""
            desc = recipe.get("description") or ""
            text_block = (name + " " + desc).lower()
            if q_lower not in text_block:
                continue
                
        if cuisine_lower:
            tags = " ".join(recipe.get("tags", [])).lower()
            if cuisine_lower not in tags:
                continue
                
        results.append(recipe)
        if len(results) >= 20:  # Top 20 for in-memory limit
            break

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
                    # Reject food.com default placeholders
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
    if recipe_id not in ml_state.recipes_dict:
        raise HTTPException(status_code=404, detail="Recipe not found in loaded catalog")
        
    return ml_state.recipes_dict[recipe_id]
