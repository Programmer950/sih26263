# Analysis Report: Baseline Test Isolation Fix (M5.1)

**Target**: `backend/tests/test_milestone_4_approval_engine.py:885` (`test_multi_tenancy_and_role_guards`)  
**Investigator**: Explorer M5.1 - 1 (`teamwork_explorer`)  
**Date**: 2026-10-30  

---

## 1. Executive Summary

When running the backend test suite (`pytest backend/tests/ -v`), 134 out of 135 tests pass cleanly. Exactly one test fails:
`backend/tests/test_milestone_4_approval_engine.py::test_multi_tenancy_and_role_guards` with:
```text
sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "uq_active_context_fingerprint"
DETAIL: Key (institution_id, programme_id, academic_year, submission_type, file_fingerprint)=(7ffb378d-9eda-4342-a727-4fb6cbc9b18b, 6b9b9092-0d19-4ee1-94ac-30aa4fd09e24, 2024-cross-01, ANNUAL_ROSTER, 8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92) already exists.
```

The root cause is a hardcoded academic year string `"2024-cross-01"` on line 885 combined with deterministic student payload data. All other tests across the suite generate isolated academic years using `f"2024-<context>-{uuid.uuid4().hex[:4]}"`. Parametrizing line 885 with a UUID hex suffix resolves the collision completely, restoring the test suite to 135/135 passing tests.

---

## 2. Root Cause Investigation

### 2.1 Database Unique Constraints Involved

1. **`uq_active_context_fingerprint`** on `source_submissions` table:
   - Defined in `backend/app/models/source_submission.py` (lines 50–59) and Alembic migration `0003_submissions_and_snapshots.py` (line 107):
     ```python
     Index(
         "uq_active_context_fingerprint",
         "institution_id",
         "programme_id",
         "academic_year",
         "submission_type",
         "file_fingerprint",
         unique=True,
         postgresql_where=text("submission_status NOT IN ('FAILED', 'CANCELLED')"),
     )
     ```
   - Purpose: Prevents duplicate active or committed submissions within the same tenant context and academic year with the identical file hash.
   - In the persistent development/test PostgreSQL database `apaar_setu`, an active row already exists:
     ```python
     (UUID('293320f1-4ade-4ffa-a139-fca5e8038562'), '2024-cross-01', 'COMMITTED', '8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92')
     ```

2. **`idx_uq_authoritative_snapshot`** on `roster_snapshots` table:
   - Defined in `backend/app/models/roster_snapshot.py` (lines 40–47):
     ```python
     Index(
         "idx_uq_authoritative_snapshot",
         "institution_id",
         "programme_id",
         "academic_year",
         unique=True,
         postgresql_where=text("is_authoritative = TRUE"),
     )
     ```
   - Even if the submission table were bypassed, having a static academic year for an authoritative snapshot (`is_authoritative=True`) collides on rerun.

### 2.2 Mechanism of Collision at Line 885

In `backend/tests/test_milestone_4_approval_engine.py`:
```python
880:     # 3. Test Cross-Institution Tenancy on Intake Verification
881:     with SessionLocal() as db:
882:         # Create a candidate snapshot belonging to Apex
883:         students = [{"name": "Apex Std", "apaar": "999900000001", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}]
884:         apex_user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()
885:         apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, "2024-cross-01", students, apex_user.id)
```

In `create_test_submission_and_snapshot`:
- A CSV is generated containing the static student record:
  `"Apex Std,999900000001,2006-01-01,M,REGULAR"`
- Its SHA-256 hash (`file_fingerprint`) is always `8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92`.
- When `db.flush()` inserts a `SourceSubmission` with `academic_year="2024-cross-01"` and `submission_status="COMMITTED"`, PostgreSQL immediately throws `UniqueViolation: duplicate key value violates unique constraint "uq_active_context_fingerprint"`.

---

## 3. Comparison with Pattern Used Across the Suite

In the same test file (`backend/tests/test_milestone_4_approval_engine.py`), every other test generates an isolated, ephemeral academic year:

| Test Name | Line # | Academic Year Pattern |
|---|---|---|
| `test_approval_configuration_lifecycle_and_amendment` | 220 | `ay = f"2024-test-{uuid.uuid4().hex[:4]}"` |
| `test_scenario_1_regular_intake_excess` | 324 | `ay = f"2024-sc1-{uuid.uuid4().hex[:4]}"` |
| `test_scenario_2_additive_supernumerary_seats` | 402 | `ay = f"2024-sc2-{uuid.uuid4().hex[:4]}"` |
| `test_scenario_3_within_sanctioned_sub_quotas` | 484 | `ay = f"2024-sc3-{uuid.uuid4().hex[:4]}"` |
| `test_scenario_4_missing_rounding_policy` | 556 | `ay = f"2024-sc4-{uuid.uuid4().hex[:4]}"` |
| `test_scenario_5_overlapping_attributes_anti_double_counting` | 619 | `ay = f"2024-sc5-{uuid.uuid4().hex[:4]}"` |
| `test_scenario_6_lateral_entry_segregated_accounting` | 690 | `ay = f"2024-sc6-{uuid.uuid4().hex[:4]}"` |
| `test_scenario_7_missing_approval_configuration_safe_fallback` | 761 | `ay = f"2024-sc7-{uuid.uuid4().hex[:4]}"` |
| `test_scenario_8_mixed_compliant_and_indeterminate_precedence` | 796 | `ay = f"2024-sc8-{uuid.uuid4().hex[:4]}"` |
| **`test_multi_tenancy_and_role_guards`** | **885** | **`"2024-cross-01"` (HARDCODED - BUG)** |

Line 885 was the single omission of this pattern in the entire suite.

---

## 4. Exact Fix Strategy for Worker

### 4.1 Target File
`backend/tests/test_milestone_4_approval_engine.py`

### 4.2 Exact Replacement Chunk
Around lines 880–886:

**Existing code:**
```python
    # 3. Test Cross-Institution Tenancy on Intake Verification
    with SessionLocal() as db:
        # Create a candidate snapshot belonging to Apex
        students = [{"name": "Apex Std", "apaar": "999900000001", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}]
        apex_user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()
        apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, "2024-cross-01", students, apex_user.id)
```

**Proposed replacement:**
```python
    # 3. Test Cross-Institution Tenancy on Intake Verification
    with SessionLocal() as db:
        # Create a candidate snapshot belonging to Apex
        students = [{"name": "Apex Std", "apaar": "999900000001", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}]
        apex_user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()
        ay = f"2024-cross-{uuid.uuid4().hex[:4]}"
        apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, apex_user.id)
```

### 4.3 Why This Is Safe and Robust
1. `uuid` is already imported at line 18 (`import uuid`).
2. `academic_year` column in PostgreSQL is `VARCHAR(20)`. The formatted string `2024-cross-xxxx` is exactly 15 characters, safely within the column limit.
3. The tenancy check under test (`POST /api/v1/approvals/intake/verify`) evaluates snapshot tenancy:
   ```python
   if actor.role.role_name == "INSTITUTION_ADMIN" and candidate.institution_id != actor.institution_id:
       raise HTTPException(status_code=403, detail="Tenancy Violation: Access to candidate snapshot for external institution forbidden.")
   ```
   The test asserts that Polytechnic admin cannot verify an Apex snapshot. The value of `academic_year` does not affect this logic; generating an ephemeral `ay` guarantees repeatable isolation without DB collision.
4. Independent verification script confirms:
   - Snapshot created cleanly.
   - Status code: `403 Forbidden`.
   - Error detail: `Tenancy Violation: Access to candidate snapshot for external institution forbidden.`
   - Clean execution across repeated runs.

---

## 5. Verification Commands for Worker

After applying the edit:
1. Run target test:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_milestone_4_approval_engine.py -k test_multi_tenancy_and_role_guards -v
   ```
   Expect: `1 passed`
2. Run target file:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_milestone_4_approval_engine.py -v
   ```
   Expect: `10 passed in ~5s`
3. Run full regression suite:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
   ```
   Expect: `135 passed, 0 failed`
