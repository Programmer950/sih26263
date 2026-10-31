"""Inspect database tables and record counts."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import SessionLocal

def inspect_db():
    db = SessionLocal()
    tables = db.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)).fetchall()

    print(f"Total tables: {len(tables)}")
    print("-" * 50)
    total_records = 0
    for (table,) in tables:
        count = db.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
        print(f"{table:35} : {count}")
        total_records += count
    print("-" * 50)
    print(f"Total records across all tables: {total_records}")

if __name__ == "__main__":
    inspect_db()

