"""
14_migrate_phase4_tables.py — Create Phase 4 tables:
  - user_preferences  (dietary tags, allergies)
  - pantry_items      (user's current pantry)
  - meal_plans        (one row per generated plan)
  - meal_plan_items   (individual day/slot entries)

Also expands the users table with email/display_name.
Safe to re-run (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

print("Creating Phase 4 tables...")
with engine.begin() as conn:

    # Expand users table
    for col in [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS supabase_uid TEXT UNIQUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
    ]:
        conn.execute(text(col))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id       INT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            dietary_tags  TEXT[] DEFAULT '{}',
            allergies     TEXT[] DEFAULT '{}',
            updated_at    TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS pantry_items (
            id              SERIAL PRIMARY KEY,
            user_id         INT NOT NULL,
            ingredient_raw  TEXT NOT NULL,
            ingredient_norm TEXT NOT NULL,
            added_at        TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (user_id, ingredient_norm)
        );

        CREATE TABLE IF NOT EXISTS meal_plans (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     INT NOT NULL,
            week_start  DATE NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (user_id, week_start)
        );

        CREATE TABLE IF NOT EXISTS meal_plan_items (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            plan_id     UUID NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
            day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
            meal_slot   TEXT NOT NULL CHECK (meal_slot IN ('breakfast','lunch','dinner')),
            recipe_id   INT REFERENCES recipes(recipe_id),
            UNIQUE (plan_id, day_of_week, meal_slot)
        );

        CREATE INDEX IF NOT EXISTS idx_pantry_user ON pantry_items(user_id);
        CREATE INDEX IF NOT EXISTS idx_mealplan_user ON meal_plans(user_id);
        CREATE INDEX IF NOT EXISTS idx_mpi_plan ON meal_plan_items(plan_id);
    """))

    # Expand interactions to support saved/cooked types
    for col in [
        "ALTER TABLE interactions ADD COLUMN IF NOT EXISTS interaction_type TEXT DEFAULT 'rated'",
        "ALTER TABLE interactions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
    ]:
        conn.execute(text(col))

print("Phase 4 tables created.")
