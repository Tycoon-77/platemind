"""
auth.py — Authentication routes via Supabase Auth.

POST /auth/signup  — Create account, insert users row, return session token.
POST /auth/login   — Authenticate, return access_token + user info.
"""
from __future__ import annotations
from typing import Optional
import os
from fastapi import APIRouter, HTTPException, Depends
from app.auth_deps import require_auth, CurrentUser
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import text

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.db import engine

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _sb_client():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# ─── Schema ──────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None
    dietary_tags: list[str] = []
    allergies: list[str] = []


class LoginRequest(BaseModel):
    email: str
    password: str


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/signup", status_code=201)
async def signup(body: SignupRequest):
    """
    1. Create Supabase Auth user (handles password hashing + email validation).
    2. Insert a row into users with supabase_uid.
    3. Insert user_preferences if dietary/allergy tags were provided.
    4. Return the access_token + user_id.
    """
    sb = _sb_client()
    try:
        # Use admin API to bypass rate limits and auto-confirm for dev
        resp = sb.auth.admin.create_user({
            "email": body.email, 
            "password": body.password,
            "email_confirm": True
        })
    except Exception as e:
        raise HTTPException(400, detail=str(e))

    if resp.user is None:
        raise HTTPException(400, detail="Signup failed — check email/password requirements")

    sb_uid = resp.user.id
    email  = resp.user.email

    # Insert into our users table (get next available user_id)
    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO users (supabase_uid, email, display_name)
            VALUES (:uid, :email, :dname)
            ON CONFLICT (supabase_uid) DO UPDATE SET email = EXCLUDED.email
            RETURNING user_id
        """), {"uid": sb_uid, "email": email, "dname": body.display_name}).fetchone()
        user_id = row.user_id

        if body.dietary_tags or body.allergies:
            conn.execute(text("""
                INSERT INTO user_preferences (user_id, dietary_tags, allergies)
                VALUES (:uid, :tags, :allg)
                ON CONFLICT (user_id) DO UPDATE SET
                    dietary_tags = EXCLUDED.dietary_tags,
                    allergies    = EXCLUDED.allergies
            """), {"uid": user_id, "tags": body.dietary_tags, "allg": body.allergies})

    access_token = getattr(resp, "session", None); access_token = access_token.access_token if access_token else None

    return {
        "user_id":     user_id,
        "supabase_uid": sb_uid,
        "email":       email,
        "access_token": access_token,
        "message":     "Account created.",
    }


@router.post("/login")
async def login(body: LoginRequest):
    """
    Authenticate with Supabase Auth; return access_token for subsequent requests.
    """
    sb = _sb_client()
    try:
        resp = sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
    except Exception as e:
        raise HTTPException(401, detail=f"Login failed: {e}")

    if resp.user is None or resp.session is None:
        raise HTTPException(401, detail="Invalid credentials")

    sb_uid = resp.user.id
    # Lookup internal user_id
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT user_id, display_name FROM users WHERE supabase_uid = :uid"),
            {"uid": sb_uid},
        ).fetchone()

    return {
        "access_token": resp.session.access_token,
        "token_type":   "bearer",
        "user_id":       row.user_id if row else None,
        "email":         resp.user.email,
        "display_name":  row.display_name if row else None,
    }

class PreferencesRequest(BaseModel):
    user_id: int
    dietary_tags: list[str] = []
    allergies: list[str] = []

def _check_owner(user_id: int, current_user: CurrentUser):
    if current_user["user_id"] != user_id:
        raise HTTPException(403, "Access denied: token does not match user_id")

@router.put("/preferences")
async def update_preferences(body: PreferencesRequest, current_user: CurrentUser = Depends(require_auth)):
    _check_owner(body.user_id, current_user)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO user_preferences (user_id, dietary_tags, allergies)
            VALUES (:uid, :tags, :allg)
            ON CONFLICT (user_id) DO UPDATE SET
                dietary_tags = EXCLUDED.dietary_tags,
                allergies    = EXCLUDED.allergies
        """), {"uid": body.user_id, "tags": body.dietary_tags, "allg": body.allergies})
    return {"message": "Preferences updated"}

@router.get("/preferences/{user_id}")
async def get_preferences(user_id: int, current_user: CurrentUser = Depends(require_auth)):
    _check_owner(user_id, current_user)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT dietary_tags, allergies FROM user_preferences WHERE user_id = :uid"), {"uid": user_id}).fetchone()
    if row:
        return {"dietary_tags": row.dietary_tags, "allergies": row.allergies}
    return {"dietary_tags": [], "allergies": []}
