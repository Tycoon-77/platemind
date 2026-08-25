"""
favorites.py — Saved / favourited recipes routes.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db import engine
from app.auth_deps import require_auth, CurrentUser

router = APIRouter()

class FavoriteRequest(BaseModel):
    recipe_id: int

def _check_owner(user_id: int, current_user: CurrentUser):
    if current_user["user_id"] != user_id:
        raise HTTPException(403, "Access denied: token does not match user_id")

@router.get("/{user_id}")
async def get_favorites(user_id: int, current_user: CurrentUser = Depends(require_auth)):
    _check_owner(user_id, current_user)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT i.recipe_id, r.name, r.minutes
            FROM interactions i
            JOIN recipes r ON i.recipe_id = r.recipe_id
            WHERE i.user_id = :uid AND i.interaction_type = 'saved'
            ORDER BY i.created_at DESC
        """), {"uid": user_id}).fetchall()
    return {
        "user_id": user_id,
        "favorites": [{"recipe_id": r.recipe_id, "name": r.name, "minutes": r.minutes} for r in rows],
    }

@router.post("/{user_id}", status_code=201)
async def add_favorite(
    user_id: int,
    body: FavoriteRequest,
    current_user: CurrentUser = Depends(require_auth),
):
    _check_owner(user_id, current_user)
    with engine.begin() as conn:
        # Check if recipe exists
        rec = conn.execute(text("SELECT 1 FROM recipes WHERE recipe_id = :rid"), {"rid": body.recipe_id}).fetchone()
        if not rec:
            raise HTTPException(404, "Recipe not found")
            
        conn.execute(text("""
            INSERT INTO interactions (user_id, recipe_id, interaction_type)
            VALUES (:uid, :rid, 'saved')
        """), {"uid": user_id, "rid": body.recipe_id})
    return {"user_id": user_id, "recipe_id": body.recipe_id, "status": "saved"}
