from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
engine = create_engine(os.environ["DATABASE_URL"])
inspector = inspect(engine)
print("Tables:", inspector.get_table_names())
for col in inspector.get_columns("recipes"):
    print(f" - {col['name']} ({col['type']})")
