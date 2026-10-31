"""Verify zero FK violations or orphan records exist in the database."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import SessionLocal

def check_integrity():
    db = SessionLocal()
    # Query exact single and composite FK constraints from pg_constraint catalog
    constraints = db.execute(text("""
        SELECT
            conname,
            conrelid::regclass::text AS source_table,
            confrelid::regclass::text AS target_table,
            ARRAY(
                SELECT attname FROM pg_attribute
                WHERE attrelid = c.conrelid AND attnum = ANY(c.conkey)
                ORDER BY array_position(c.conkey, attnum)
            ) AS source_columns,
            ARRAY(
                SELECT attname FROM pg_attribute
                WHERE attrelid = c.confrelid AND attnum = ANY(c.confkey)
                ORDER BY array_position(c.confkey, attnum)
            ) AS target_columns
        FROM pg_constraint c
        WHERE contype = 'f' AND connamespace = 'public'::regnamespace;
    """)).fetchall()

    print(f"Total Foreign Key Constraints Checked: {len(constraints)}")
    orphans = 0
    for name, src_tbl, tgt_tbl, src_cols, tgt_cols in constraints:
        join_conds = [f't."{s}" = ft."{t}"' for s, t in zip(src_cols, tgt_cols)]
        not_null_conds = [f't."{s}" IS NOT NULL' for s in src_cols]
        q = f'''
            SELECT count(*) FROM {src_tbl} t
            WHERE {' AND '.join(not_null_conds)}
              AND NOT EXISTS (
                SELECT 1 FROM {tgt_tbl} ft
                WHERE {' AND '.join(join_conds)}
              );
        '''
        count = db.execute(text(q)).scalar()
        if count > 0:
            print(f"ORPHAN DETECTED: {src_tbl}({','.join(src_cols)}) -> {tgt_tbl}({','.join(tgt_cols)}): {count}")
            orphans += count

    if orphans == 0:
        print("PERFECT: Zero orphan rows or foreign key violations detected across all database tables.")
    else:
        print(f"WARNING: {orphans} total orphan foreign key rows found.")

if __name__ == "__main__":
    check_integrity()
