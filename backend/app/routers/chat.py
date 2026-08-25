"""
chat.py — Conversational RAG chat route.

POST /chat
  Body:    { session_id: str, message: str, user_id?: int }
  Response: { reply, session_id, retrieved_recipe_ids, updated_results,
              intent, from_cache }

Design:
  - Retrieval: pgvector cosine similarity (via rag_chain.py).
  - LLM: Groq (llama-3.3-70b-versatile).
  - TTL cache: 60 s on identical (session_id, message) pairs.
  - Rate-limit: clean fallback message, never a raw 429/500.
  - Persistence: exchanges stored in chat_sessions / chat_messages (Supabase).
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Request
from app.limiter import limiter
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db import engine
from app.services.rag_chain import invoke_rag

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str          # UUID string; pass "new" to auto-create
    message:    str
    user_id:    Optional[int] = None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ensure_session(conn, session_id: str, user_id: Optional[int]) -> str:
    """Create chat_sessions row if it doesn't exist; return resolved session_id."""
    if session_id == "new":
        session_id = str(uuid.uuid4())

    row = conn.execute(
        text("SELECT id FROM chat_sessions WHERE id = CAST(:sid AS uuid)"),
        {"sid": session_id},
    ).fetchone()

    if not row:
        conn.execute(
            text("""
                INSERT INTO chat_sessions (id, user_id)
                VALUES (CAST(:sid AS uuid), :uid)
                ON CONFLICT (id) DO NOTHING
            """),
            {"sid": session_id, "uid": user_id},
        )

    return session_id


def _load_history(conn, session_id: str, last_n: int = 6) -> list[dict]:
    """Return the last N messages for the session as [{"role", "content"}]."""
    rows = conn.execute(
        text("""
            SELECT role, content FROM chat_messages
            WHERE session_id = CAST(:sid AS uuid)
            ORDER BY created_at DESC LIMIT :n
        """),
        {"sid": session_id, "n": last_n},
    ).fetchall()
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def _save_messages(conn, session_id: str, user_msg: str, assistant_reply: str, recipe_ids: list[int]):
    conn.execute(
        text("""
            INSERT INTO chat_messages (session_id, role, content, retrieved_recipe_ids)
            VALUES
              (CAST(:sid AS uuid), 'user',      :umsg, '{}'),
              (CAST(:sid AS uuid), 'assistant', :amsg, :rids)
        """),
        {
            "sid":  session_id,
            "umsg": user_msg,
            "amsg": assistant_reply,
            "rids": recipe_ids,
        },
    )
    # bump updated_at on the session
    conn.execute(
        text("UPDATE chat_sessions SET updated_at = NOW() WHERE id = CAST(:sid AS uuid)"),
        {"sid": session_id},
    )


# ---------------------------------------------------------------------------
# route
# ---------------------------------------------------------------------------

@router.post("")
async def chat(body: ChatRequest):
    """Process a message through the RAG chain and persist the exchange."""
    if not body.message.strip():
        raise HTTPException(400, "message must not be empty")

    try:
        with engine.begin() as conn:
            session_id = _ensure_session(conn, body.session_id, body.user_id)
            history    = _load_history(conn, session_id)

        # RAG call (outside the transaction — can be slow)
        rag_result = invoke_rag(
            message=body.message,
            session_id=session_id,
            history=history,
        )

        # Persist (skip if from cache — messages already saved on first call)
        if not rag_result.get("from_cache"):
            with engine.begin() as conn:
                _save_messages(
                    conn,
                    session_id=session_id,
                    user_msg=body.message,
                    assistant_reply=rag_result["reply"],
                    recipe_ids=rag_result["retrieved_recipe_ids"],
                )

        return {
            "session_id":           session_id,
            "reply":                rag_result["reply"],
            "intent":               rag_result["intent"],
            "retrieved_recipe_ids": rag_result["retrieved_recipe_ids"],
            "updated_results":      rag_result["updated_results"],
            "from_cache":           rag_result["from_cache"],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, detail=str(e))
