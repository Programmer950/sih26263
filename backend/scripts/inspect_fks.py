"""Inspect foreign key dependencies across all public tables."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import SessionLocal

def inspect_foreign_keys():
    db = SessionLocal()
    fks = db.execute(text("""
        SELECT
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints AS rc
          ON rc.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
        ORDER BY tc.table_name, kcu.column_name;
    """)).fetchall()

    print(f"Total Foreign Keys: {len(fks)}")
    print("-" * 80)
    for row in fks:
        print(f"{row[0]:32} . {row[1]:28} -> {row[2]:30} . {row[3]} ({row[4]})")

if __name__ == "__main__":
    inspect_foreign_keys()

