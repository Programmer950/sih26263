"""
APAAR SETU — Controlled Demo Database Reset Script
Safely removes synthetic institutional and student demonstration data
while preserving schema, migrations, user authentication, RBAC roles, and audit infrastructure.
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timezone
import uuid
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text, select
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models import AuditEvent, User
from app.services.snapshot_service import SnapshotService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("apaar_setu.demo_reset")

# Tables to clean, in exact reverse-topological dependency order
DEMO_TABLES_ORDER = [
    "verification_requests",
    "discrepancy_case_decisions",
    "reconciliation_result_items",
    "discrepancy_cases",
    "intake_reconciliation_summaries",
    "aggregate_enrolment_declarations",
    "reconciliation_runs",
    "annual_roster_observations",
    "approval_category_allocations",
    "approval_configurations",
    "roster_snapshots",
    "submission_previews",
    "source_submission_records",
    "source_submissions",
    "transfer_events",
    "admission_episodes",
    "institution_student_records",
    "student_identities",
    "programmes",
    "institutions",
]

PRESERVED_TABLES = [
    "alembic_version",
    "roles",
    "users",
    "session_revocations",
    "audit_events",
]


def verify_safety_guards(confirm_flag: bool):
    """Enforces execution environment guards."""
    env = getattr(settings, "ENVIRONMENT", "").lower()
    if env not in ("development", "test", "demo", "dev"):
        logger.error(f"ABORTED: Refusing to reset data in environment '{env}'. Only development/demo allowed.")
        sys.exit(1)

    if not confirm_flag:
        logger.error("ABORTED: Missing required safety flag '--confirm-reset-demo-data'.")
        sys.exit(1)


def get_table_counts(db) -> dict:
    """Returns row counts for all application tables."""
    counts = {}
    for tbl in DEMO_TABLES_ORDER + PRESERVED_TABLES:
        cnt = db.execute(text(f'SELECT count(*) FROM "{tbl}"')).scalar()
        counts[tbl] = cnt
    return counts


def execute_reset(db) -> dict:
    """Executes the controlled reset within a single atomic transaction."""
    logger.info("Starting controlled demo database reset...")
    deleted_counts = {}

    # 1. Null out self-referencing foreign keys first
    logger.info("Breaking self-referential foreign keys...")
    db.execute(text("UPDATE approval_configurations SET superseded_by_id = NULL WHERE superseded_by_id IS NOT NULL;"))
    db.execute(text("UPDATE roster_snapshots SET superseded_by_snapshot_id = NULL WHERE superseded_by_snapshot_id IS NOT NULL;"))

    # 2. Disassociate users from demo institutions (preserve users and roles!)
    logger.info("Preserving user accounts: disassociating institution_id from users...")
    users_updated = db.execute(text("UPDATE users SET institution_id = NULL WHERE institution_id IS NOT NULL;")).rowcount
    logger.info(f"Disassociated {users_updated} user account(s) from demo institutions.")

    # 3. Delete records from demo tables in reverse dependency order
    for table in DEMO_TABLES_ORDER:
        result = db.execute(text(f'DELETE FROM "{table}";'))
        deleted_counts[table] = result.rowcount
        logger.info(f"Deleted {result.rowcount:6d} records from '{table}'")

    # 4. Record controlled reset in audit ledger
    system_user = db.execute(
        text("SELECT id FROM users WHERE email IN ('admin@setu.gov.in', 'sysadmin@aicte.gov.in') LIMIT 1;")
    ).scalar()

    SnapshotService.record_chained_audit_event(
        db=db,
        actor_id=system_user or uuid.uuid4(),
        action="CONTROLLED_DEMO_DATA_RESET",
        entity_type="SystemEnvironment",
        entity_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        metadata_payload={
            "action": "CONTROLLED_DEMO_DATA_RESET",
            "deleted_counts": deleted_counts,
            "reason": "Pre-import cleanup for manually curated CSV dataset",
        },
    )
    logger.info("Recorded cryptographic audit ledger entry for demo data reset.")

    return deleted_counts


def main():
    parser = argparse.ArgumentParser(description="Controlled Demo Database Reset for APAAR SETU")
    parser.add_argument(
        "--confirm-reset-demo-data",
        action="store_true",
        help="Mandatory safety confirmation flag to execute demo reset.",
    )
    args = parser.parse_args()

    verify_safety_guards(args.confirm_reset_demo_data)

    db = SessionLocal()
    try:
        logger.info("Fetching pre-reset table record counts...")
        pre_counts = get_table_counts(db)

        # Execute reset and commit
        deleted_counts = execute_reset(db)
        db.commit()

        logger.info("Fetching post-reset table record counts...")
        post_counts = get_table_counts(db)

        print("\n" + "=" * 70)
        print("APAAR SETU — CONTROLLED DEMO RESET SUMMARY")
        print("=" * 70)
        print(f"{'Table Name':35} | {'Pre-Count':>10} | {'Deleted':>10} | {'Post-Count':>10}")
        print("-" * 70)

        total_deleted = 0
        for tbl in DEMO_TABLES_ORDER:
            pre = pre_counts.get(tbl, 0)
            dlt = deleted_counts.get(tbl, 0)
            post = post_counts.get(tbl, 0)
            total_deleted += dlt
            print(f"{tbl:35} | {pre:10d} | {dlt:10d} | {post:10d}")

        print("-" * 70)
        print("PRESERVED SYSTEM TABLES:")
        print("-" * 70)
        for tbl in PRESERVED_TABLES:
            pre = pre_counts.get(tbl, 0)
            post = post_counts.get(tbl, 0)
            print(f"{tbl:35} | {pre:10d} | {'(PRESERVED)':>10} | {post:10d}")

        print("=" * 70)
        print(f"Total demo records removed: {total_deleted}")
        print("Database is now clean and ready for curated CSV dataset ingestion.")
        print("=" * 70)

    except Exception as exc:
        logger.error(f"Controlled reset failed: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
