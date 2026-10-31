# Handoff Report: Test Isolation Fix Strategy for Milestone 5.1

**Agent**: Explorer M5.1 - 1 (`teamwork_explorer`)  
**Working Directory**: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_m5_1_1\`  
**Target File**: `backend/tests/test_milestone_4_approval_engine.py`  
**Handoff Type**: Hard (Investigation complete, actionable fix prepared)  

---

## 1. Observation

1. **Test Failure Verbatim**:
   Running `.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_milestone_4_approval_engine.py -k test_multi_tenancy_and_role_guards -v`:
   ```text
   sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "uq_active_context_fingerprint"
   DETAIL: Key (institution_id, programme_id, academic_year, submission_type, file_fingerprint)=(7ffb378d-9eda-4342-a727-4fb6cbc9b18b, 6b9b9092-0d19-4ee1-94ac-30aa4fd09e24, 2024-cross-01, ANNUAL_ROSTER, 8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92) already exists.
   [SQL: INSERT INTO source_submissions (id, institution_id, programme_id, academic_year, submission_type, submission_status, original_filename, storage_key, file_fingerprint, ...) VALUES ...]
   ```

2. **Constraint Definitions**:
   - `backend/app/models/source_submission.py` lines 50–59:
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
   - `backend/app/models/roster_snapshot.py` lines 40–47:
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

3. **Current Database State in PostgreSQL (`apaar_setu`)**:
   Inspecting `source_submissions`:
   ```python
   (UUID('293320f1-4ade-4ffa-a139-fca5e8038562'), '2024-cross-01', 'COMMITTED', '8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92')
   ```
   An existing active committed record occupies `academic_year = '2024-cross-01'`.

4. **Line 885 Implementation**:
   In `backend/tests/test_milestone_4_approval_engine.py:880-886`:
   ```python
   # 3. Test Cross-Institution Tenancy on Intake Verification
   with SessionLocal() as db:
       # Create a candidate snapshot belonging to Apex
       students = [{"name": "Apex Std", "apaar": "999900000001", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}]
       apex_user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()
       apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, "2024-cross-01", students, apex_user.id)
   ```
   The string `"2024-cross-01"` is hardcoded.

5. **Parametrization Patterns in All Other Tests**:
   Throughout `backend/tests/test_milestone_4_approval_engine.py`:
   - Line 220: `ay = f"2024-test-{uuid.uuid4().hex[:4]}"`
   - Line 324: `ay = f"2024-sc1-{uuid.uuid4().hex[:4]}"`
   - Line 402: `ay = f"2024-sc2-{uuid.uuid4().hex[:4]}"`
   - Line 484: `ay = f"2024-sc3-{uuid.uuid4().hex[:4]}"`
   - Line 556: `ay = f"2024-sc4-{uuid.uuid4().hex[:4]}"`
   - Line 619: `ay = f"2024-sc5-{uuid.uuid4().hex[:4]}"`
   - Line 690: `ay = f"2024-sc6-{uuid.uuid4().hex[:4]}"`
   - Line 761: `ay = f"2024-sc7-{uuid.uuid4().hex[:4]}"`
   - Line 796: `ay = f"2024-sc8-{uuid.uuid4().hex[:4]}"`

6. **Regression Baseline Execution**:
   - Running full test suite excluding the single test:
     `.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -k "not test_multi_tenancy_and_role_guards" -q`
     Result: `134 passed, 1 deselected in 38.94s`.
   - Running proposed fix dynamically via Python test script:
     Created snapshot cleanly (`63211b3e-05e1-454d-b7b9-6208e258378f`), received HTTP 403 Forbidden with detail `"Tenancy Violation: Access to candidate snapshot for external institution forbidden."`. Verification succeeded.

---

## 2. Logic Chain

1. **Step 1 (From Observation 1 & 3)**: The test failure is caused by a unique constraint violation when inserting a row into `source_submissions` with `(institution_id, programme_id, '2024-cross-01', 'ANNUAL_ROSTER', '8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92')`. A row with these exact values already exists in the PostgreSQL database from a previous test run.
2. **Step 2 (From Observation 2 & 4)**: In `test_multi_tenancy_and_role_guards`, the student list is static (`Apex Std`, APAAR `999900000001`), producing the identical SHA-256 fingerprint every run. Line 885 hardcodes the academic year to `"2024-cross-01"`. Because PostgreSQL persistence retains records across runs, the second and all subsequent executions fail on the partial unique index `uq_active_context_fingerprint`.
3. **Step 3 (From Observation 5)**: Every other test in `backend/tests/test_milestone_4_approval_engine.py` generates a unique academic year using `uuid.uuid4().hex[:4]` (`2024-sc1-xxxx`, `2024-sc2-xxxx`, etc.). This guarantees each test operates in its own isolated relational context and never collides with past test executions.
4. **Step 4 (From Observation 6)**: The test `test_multi_tenancy_and_role_guards` only tests that a Polytechnic admin token cannot verify an Apex candidate snapshot (`candidate.institution_id != actor.institution_id`). The academic year string is not checked or asserted in this test; it only anchors the snapshot. Therefore, parametrizing the academic year with `ay = f"2024-cross-{uuid.uuid4().hex[:4]}"` is completely non-breaking, robust, and restores test isolation.

---

## 3. Caveats

- **Assumption**: Tests run against the local development/test PostgreSQL database `apaar_setu`. The database is not dropped or re-created between pytest sessions, so tests must be idempotent and isolated by randomizing context identifiers.
- **Alternative Considered**: Truncating the `source_submissions` table between tests. Rejected because it breaks test parallelism, risks destroying seeded demo/institutional records, and violates the established project convention where each test creates isolated academic year namespaces.
- **Scope Limit**: This investigation only covers fixing line 885. Explorer M5.1 - 2 has separately addressed the E2E harness architecture.

---

## 4. Conclusion

The exact, minimal, robust fix for the test isolation collision is:
In `backend/tests/test_milestone_4_approval_engine.py`, replace line 885 with:
```python
        ay = f"2024-cross-{uuid.uuid4().hex[:4]}"
        apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, apex_user.id)
```

### Exact Code Edit for Worker:
Target file: `backend/tests/test_milestone_4_approval_engine.py` (lines 881–886):

```python
<<<<
    with SessionLocal() as db:
        # Create a candidate snapshot belonging to Apex
        students = [{"name": "Apex Std", "apaar": "999900000001", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}]
        apex_user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()
        apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, "2024-cross-01", students, apex_user.id)
====
    with SessionLocal() as db:
        # Create a candidate snapshot belonging to Apex
        students = [{"name": "Apex Std", "apaar": "999900000001", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}]
        apex_user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()
        ay = f"2024-cross-{uuid.uuid4().hex[:4]}"
        apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, apex_user.id)
>>>>
```

---

## 5. Verification Method

To verify the fix independently, Worker must run:

1. **Verify single test passes**:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_milestone_4_approval_engine.py -k test_multi_tenancy_and_role_guards -v
   ```
   **Expected**: `1 passed`

2. **Verify all tests in `test_milestone_4_approval_engine.py` pass**:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_milestone_4_approval_engine.py -v
   ```
   **Expected**: `10 passed in ~5s`

3. **Verify complete 135-test regression baseline passes**:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
   ```
   **Expected**: `135 passed, 0 failed`

**Invalidation Conditions**:
- If `test_multi_tenancy_and_role_guards` still raises `IntegrityError` or fails assertion `assert res_cross_verify.status_code == 403`.
