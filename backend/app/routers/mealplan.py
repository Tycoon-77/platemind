"""
mealplan.py — Meal plan routes backed by Postgres.
"""
from __future__ import annotations
import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app import ml_state
from app.db import engine
from app.auth_deps import require_auth, CurrentUser
from app.routers.recommend import _apply_dietary_filter, _fetch_recipes_by_ids

router = APIRouter()

class UpdateMealSlotRequest(BaseModel):
    recipe_id: int

def _check_owner(user_id: int, current_user: CurrentUser):
    if current_user["user_id"] != user_id:
        raise HTTPException(403, "Access denied: token does not match user_id")

@router.get("/{user_id}/current")
async def get_current_meal_plan(user_id: int, current_user: CurrentUser = Depends(require_auth)):
    _check_owner(user_id, current_user)
    with engine.connect() as conn:
        plan_row = conn.execute(text("""
            SELECT id, week_start FROM meal_plans
            WHERE user_id = :uid ORDER BY week_start DESC LIMIT 1
        """), {"uid": user_id}).fetchone()
        
        if not plan_row:
            return {"user_id": user_id, "meal_plan": None}
            
        items = conn.execute(text("""
            SELECT mpi.day_of_week, mpi.meal_slot, r.recipe_id, r.name, r.minutes
            FROM meal_plan_items mpi
            LEFT JOIN recipes r ON mpi.recipe_id = r.recipe_id
            WHERE mpi.plan_id = :pid
        """), {"pid": plan_row.id}).fetchall()
        
    slots = []
    for it in items:
        slots.append({
            "day": it.day_of_week,
            "slot": it.meal_slot,
            "recipe_id": it.recipe_id,
            "name": it.name,
            "minutes": it.minutes
        })
        
    return {
        "user_id": user_id,
        "meal_plan": {
            "plan_id": str(plan_row.id),
            "week_start": str(plan_row.week_start),
            "slots": slots
        }
    }

@router.post("/{user_id}/generate", status_code=201)
async def generate_meal_plan(user_id: int, current_user: CurrentUser = Depends(require_auth)):
    _check_owner(user_id, current_user)
    
    if ml_state.mf_model is None:
        raise HTTPException(500, "ML models not loaded")
        
    # Get user dietary tags
    with engine.connect() as conn:
        pref = conn.execute(text("SELECT dietary_tags FROM user_preferences WHERE user_id = :uid"), {"uid": user_id}).fetchone()
        tags = pref.dietary_tags if pref else []
        
    # Generate 21 recommendations
    from scipy.sparse import csr_matrix
    n_items = ml_state.mf_model.model_.item_factors.shape[0]
    dummy = csr_matrix((1, n_items))
    u_idx = 0
    if user_id in ml_state.mf_model.user_enc_.classes_:
        u_idx = int(ml_state.mf_model.user_enc_.transform([user_id])[0])
        
    # Ask for enough items so we have 21 after filtering
    recs_idx, _ = ml_state.mf_model.model_.recommend(
        u_idx, dummy, N=2000, filter_already_liked_items=False
    )
    original_rids = ml_state.mf_model.item_enc_.inverse_transform(recs_idx).tolist()
    
    with engine.connect() as conn:
        if True:
            original_rids = _apply_dietary_filter(conn, original_rids, tags)
    
    if len(original_rids) < 7:
        raise HTTPException(400, "Not enough recipes match your dietary preferences to build a plan.")
        
    # Just fill dinner for 7 days for now to ensure we have enough, or 3 slots if we have 21
    # Let's do just dinners to be safe, or up to 21 if possible.
    slots_needed = [(d, "dinner") for d in range(7)]
    if len(original_rids) >= 21:
        slots_needed = [(d, s) for d in range(7) for s in ["breakfast", "lunch", "dinner"]]
        
    chosen_rids = original_rids[:len(slots_needed)]
    
    week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    
    with engine.begin() as conn:
        # Upsert meal plan
        plan_row = conn.execute(text("""
            INSERT INTO meal_plans (user_id, week_start)
            VALUES (:uid, :ws)
            ON CONFLICT (user_id, week_start) DO UPDATE SET week_start = EXCLUDED.week_start
            RETURNING id
        """), {"uid": user_id, "ws": week_start}).fetchone()
        
        plan_id = plan_row.id
        
        # Clear existing items for this plan
        conn.execute(text("DELETE FROM meal_plan_items WHERE plan_id = :pid"), {"pid": plan_id})
        
        for i, (day, slot) in enumerate(slots_needed):
            conn.execute(text("""
                INSERT INTO meal_plan_items (plan_id, day_of_week, meal_slot, recipe_id)
                VALUES (:pid, :day, :slot, :rid)
            """), {"pid": plan_id, "day": day, "slot": slot, "rid": chosen_rids[i]})
            
    # Return it via the get endpoint logic
    return await get_current_meal_plan(user_id, current_user)

@router.patch("/{plan_id}/{day}/{slot}")
async def update_meal_slot(
    plan_id: str, 
    day: int, 
    slot: str, 
    body: UpdateMealSlotRequest,
    current_user: CurrentUser = Depends(require_auth)
):
    with engine.begin() as conn:
        # Verify plan ownership
        owner = conn.execute(text("SELECT user_id FROM meal_plans WHERE id = :pid"), {"pid": plan_id}).fetchone()
        if not owner or owner.user_id != current_user["user_id"]:
            raise HTTPException(403, "Plan not found or access denied")
            
        conn.execute(text("""
            UPDATE meal_plan_items
            SET recipe_id = :rid
            WHERE plan_id = :pid AND day_of_week = :day AND meal_slot = :slot
        """), {"rid": body.recipe_id, "pid": plan_id, "day": day, "slot": slot})
        
    return {"plan_id": plan_id, "day": day, "slot": slot, "recipe_id": body.recipe_id}
