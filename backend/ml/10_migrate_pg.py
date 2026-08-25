import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in backend/.env")
    print("Please provision a Postgres database with pgvector (e.g. Supabase) and add it.")
    exit(1)

# SQLAlchemy requires postgresql:// instead of postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("============================================================")
print("PHASE 2 — Step 10: Migrate to Postgres (pgvector)")
print("============================================================")

engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    print("[1/3] Enabling pgvector extension...")
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    print("[2/3] Creating tables...")
    conn.execute(text("""
        DROP TABLE IF EXISTS interactions CASCADE;
        DROP TABLE IF EXISTS recipes CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            user_id INT UNIQUE
        );
        
        CREATE TABLE recipes (
            id SERIAL PRIMARY KEY,
            recipe_id INT UNIQUE,
            name VARCHAR(255),
            minutes INT,
            tags TEXT[],
            ingredients TEXT[],
            embedding vector(384)
        );
        
        CREATE TABLE interactions (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(user_id),
            recipe_id INT REFERENCES recipes(recipe_id),
            rating INT
        );
    """))

print("[3/3] Tables created successfully. Ready for data ingestion.")
print("To bulk load data, run df.to_sql() or use COPY. (Skipped for demo brevity)")
