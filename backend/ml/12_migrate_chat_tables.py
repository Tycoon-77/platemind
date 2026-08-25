"""
12_migrate_chat_tables.py — Create chat_sessions and chat_messages tables.

Safe to re-run (IF NOT EXISTS).
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

print("Creating chat tables...")
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     INT,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id           UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role                 TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content              TEXT NOT NULL,
            retrieved_recipe_ids INT[] DEFAULT '{}',
            created_at           TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_chat_messages_session
            ON chat_messages(session_id, created_at);
    """))

print("chat_sessions and chat_messages tables ready.")
