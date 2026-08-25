"""
auth_deps.py — FastAPI dependency for JWT auth via Supabase.

Usage in any router:
    from app.auth_deps import require_auth, CurrentUser
    @router.get("/")
    async def handler(user: CurrentUser = Depends(require_auth)):
        ...

CurrentUser is a TypedDict with keys: uid (str), email (str), user_id (int|None).
"""
from typing import Optional
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_bearer = HTTPBearer(auto_error=False)


def _get_supabase():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


async def require_auth(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    Validate a Supabase JWT from the Authorization: Bearer <token> header.
    Returns a dict with uid, email, user_id (our internal int id).
    Raises 401 if token is missing or invalid.
    """
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Missing auth token")

    token = creds.credentials
    sb = _get_supabase()
    try:
        user_resp = sb.auth.get_user(token)
        sb_user = user_resp.user
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Invalid token: {e}")

    if sb_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token has expired or is invalid")

    # Look up our internal user_id
    from app.db import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT user_id FROM users WHERE supabase_uid = :uid"),
            {"uid": sb_user.id},
        ).fetchone()
    internal_id = row.user_id if row else None

    return {"uid": sb_user.id, "email": sb_user.email, "user_id": internal_id}


# Convenient type alias
CurrentUser = dict
