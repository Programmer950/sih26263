# Analysis Report: Regression Safeguards & Implementation Plan for Worker M5.1-It2

**Agent**: explorer_m5_1_it2_3 (`teamwork_explorer`)  
**Mission**: Verify test regression safeguards, execution performance, and synthesize an exact, error-proof implementation plan for Worker M5.1 Iteration 2.  
**Target File**: `backend/tests/test_e2e_integration.py`  
**Date**: 2026-10-30  

---

## 1. Executive Summary

During Milestone 5.1 review, Reviewers identified a defect in `is_route_mounted` inside `backend/tests/test_e2e_integration.py`:
- In FastAPI 0.115+, `app.include_router(..., prefix="/api/v1")` wraps routers in `fastapi.routing._IncludedRouter`.
- Top-level `route.path` on `_IncludedRouter` is `None`, which caused `is_route_mounted` to evaluate to `False` for **all** `/api/v1` endpoints, including existing mounted ones.
- If unaddressed, this defect would cause the 23 progressive integration tests to remain permanently skipped even when M5.2, M5.3, and M5.4 endpoints are added.
- In addition, line 1174 contained a test naming typo (`test_t1_r2_04_reconciliation_comparison_csv_export` instead of `test_t1_r5_04_reconciliation_comparison_csv_export`).

This investigation empirically verifies:
1. **Zero Premature Activation**: When `is_route_mounted` is fixed to inspect `route.effective_candidates()`, **0 out of 23** skipped tests activate prematurely. All 23 tests continue to skip safely because their corresponding endpoints (`/api/v1/reconciliation/unified`, `/api/v1/reconciliation/duplicates`, `/api/v1/verification/request`, `/api/v1/verification/qr/{token}`, `/api/v1/dashboard/summary`) are genuinely not yet implemented in the backend.
2. **100% Stability of Active Tests**: All **48 active integration tests** continue to pass with zero failures.
3. **Execution Performance Preserved**: Full execution of `test_e2e_integration.py` completes in **19.11s** (virtually identical to baseline 18.86s).
4. **Future Activation Verified**: Simulating route registration for M5.2 and M5.3 confirms that `is_route_mounted` immediately detects new endpoints and activates the corresponding tests without further harness modifications.

---

## 2. Empirical Verification of Route Probing

### 2.1 Current App Route Traversal

Inspecting `app.routes` directly reveals 13 top-level items:
- 5 root routes: `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`, `/health`
- 8 `_IncludedRouter` instances representing the mounted subrouters under `/api/v1`

When `effective_candidates()` is called on each `_IncludedRouter`, exactly **46 distinct endpoints** are resolved:
- `/api/v1/auth/...` (3 endpoints)
- `/api/v1/institutions/...` (5 endpoints)
- `/api/v1/students/...` (4 endpoints)
- `/api/v1/submissions/...` (6 endpoints)
- `/api/v1/snapshots/...` (6 endpoints)
- `/api/v1/reconciliation/...` (4 endpoints: `/runs` POST/GET, `/runs/{id}` GET, `/runs/{id}/results` GET)
- `/api/v1/discrepancies/...` (4 endpoints)
- `/api/v1/approvals/...` (8 endpoints)
- Root endpoints (6 endpoints including `/health`)

### 2.2 Probing Existing vs. Unimplemented Endpoints

Executing the fixed `is_route_mounted` against both mounted and unmounted endpoints confirms:

| Route Path | Method | Expected | Fixed `is_route_mounted` Result | Verification Status |
|---|---|---|---|---|
| `/health` | `GET` | `True` (mounted) | `True` | Verified |
| `/api/v1/auth/login` | `POST` | `True` (mounted) | `True` | Verified |
| `/api/v1/auth/me` | `GET` | `True` (mounted) | `True` | Verified |
| `/api/v1/submissions/upload` | `POST` | `True` (mounted) | `True` | Verified |
| `/api/v1/reconciliation/runs` | `POST` | `True` (mounted) | `True` | Verified |
| `/api/v1/snapshots/123/export` | `GET` | `True` (param match) | `True` | Verified |
| `/api/v1/reconciliation/unified` | `POST` | `False` (M5.2 pending) | `False` | Verified |
| `/api/v1/reconciliation/duplicates` | `GET` | `False` (M5.2 pending) | `False` | Verified |
| `/api/v1/verification/request` | `POST` | `False` (M5.3 pending) | `False` | Verified |
| `/api/v1/verification/qr/token123` | `GET` | `False` (M5.3 pending) | `False` | Verified |
| `/api/v1/verification/qr/{token}` | `GET` | `False` (M5.3 pending) | `False` | Verified |
| `/api/v1/dashboard/summary` | `GET` | `False` (M5.4 pending) | `False` | Verified |

### 2.3 Comprehensive Audit of the 23 Skipped Tests

All 23 tests guarded by `is_route_mounted` were mapped against their tested endpoint and target milestone:

| # | Test Function Name | Line | Endpoint Checked | Method | Milestone |
|---|---|---|---|---|---|
| 1 | `test_t1_r2_03_unified_reconciliation_pipeline_joint_execution` | 536 | `/api/v1/reconciliation/unified` | `POST` | M5.2 |
| 2 | `test_t1_r2_04_cross_institution_duplicate_detection_by_blind_index` | 559 | `/api/v1/reconciliation/duplicates` | `GET` | M5.2 |
| 3 | `test_t2_r2_04_duplicate_detection_ignores_non_concurrent_years` | 695 | `/api/v1/reconciliation/duplicates` | `GET` | M5.2 |
| 4 | `test_t1_r4_01_third_party_verifier_request_returns_verified_status` | 965 | `/api/v1/verification/request` | `POST` | M5.3 |
| 5 | `test_t1_r4_02_minimal_field_disclosure_whitelist_enforced` | 984 | `/api/v1/verification/request` | `POST` | M5.3 |
| 6 | `test_t1_r4_03_authenticable_token_and_qr_payload_generation` | 1009 | `/api/v1/verification/request` | `POST` | M5.3 |
| 7 | `test_t1_r4_04_qr_verification_endpoint_validates_token` | 1030 | `/api/v1/verification/qr/{token}` | `GET` | M5.3 |
| 8 | `test_t1_r4_05_verification_purpose_ledger_audit_logging` | 1039 | `/api/v1/verification/request` | `POST` | M5.3 |
| 9 | `test_t2_r4_01_missing_consent_confirmation_rejected` | 1053 | `/api/v1/verification/request` | `POST` | M5.3 |
| 10 | `test_t2_r4_02_non_existent_apaar_returns_not_found` | 1071 | `/api/v1/verification/request` | `POST` | M5.3 |
| 11 | `test_t2_r4_03_tampered_or_expired_qr_token_returns_invalid` | 1091 | `/api/v1/verification/qr/{token}` | `GET` | M5.3 |
| 12 | `test_t2_r4_04_unauthenticated_or_unauthorised_verification_blocked` | 1102 | `/api/v1/verification/request` | `POST` | M5.3 |
| 13 | `test_t2_r4_05_blank_or_whitespace_purpose_rejected` | 1114 | `/api/v1/verification/request` | `POST` | M5.3 |
| 14 | `test_t1_r5_01_institution_admin_dashboard_summary_scoped` | 1134 | `/api/v1/dashboard/summary` | `GET` | M5.4 |
| 15 | `test_t1_r5_02_regulatory_reviewer_dashboard_summary_system_wide` | 1147 | `/api/v1/dashboard/summary` | `GET` | M5.4 |
| 16 | `test_t2_r5_01_institution_admin_cannot_query_foreign_dashboard` | 1212 | `/api/v1/dashboard/summary` | `GET` | M5.4 |
| 17 | `test_t2_r5_04_empty_programme_dashboard_zero_division_safety` | 1255 | `/api/v1/dashboard/summary` | `GET` | M5.4 |
| 18 | `test_t2_r5_05_unauthenticated_dashboard_access_returns_401` | 1265 | `/api/v1/dashboard/summary` | `GET` | M5.4 |
| 19 | `test_t1_r6_04_cross_institution_duplicate_flagged_in_unified_run` | 1307 | `/api/v1/reconciliation/duplicates` | `GET` | M5.2 |
| 20 | `test_t3_cross_02_discrepancy_resolution_reflects_in_dashboard_kpis` | 1474 | `/api/v1/dashboard/summary` | `GET` | M5.4 |
| 21 | `test_t3_cross_03_submission_confirmation_enables_immediate_third_party_verification` | 1484 | `/api/v1/verification/request` | `POST` | M5.3 |
| 22 | `test_t3_cross_05_verification_privacy_whitelisting_under_active_discrepancy` | 1521 | `/api/v1/verification/request` | `POST` | M5.3 |
| 23 | `test_t4_scenario_4_external_verifier_purpose_stated_request_and_qr_check` | 1640 | `/api/v1/verification/request` | `POST` | M5.3 |

**Result**: Because None of these 5 endpoints (`/api/v1/reconciliation/unified`, `/api/v1/reconciliation/duplicates`, `/api/v1/verification/request`, `/api/v1/verification/qr/{token}`, `/api/v1/dashboard/summary`) are currently registered in `app.routes`, fixing `is_route_mounted` guarantees that all 23 tests continue to skip cleanly.

### 2.4 Simulation of Future Milestone Activation

To verify forward compatibility for subsequent milestone workers:
1. Adding a dummy route `@reconciliation_router.post('/unified')` on the existing router dynamically activates `is_route_mounted('/api/v1/reconciliation/unified', 'POST') -> True`.
2. Including a new router via `app.include_router(verification_router, prefix='/api/v1')` dynamically activates `is_route_mounted('/api/v1/verification/request', 'POST') -> True` and `is_route_mounted('/api/v1/verification/qr/{token}', 'GET') -> True`.

This guarantees that future milestones will automatically activate their assigned test cases upon registering their endpoints.

---

## 3. Empirical Test Execution with Fixed Function

An in-memory monkeypatched execution was run using Python 3.13 and Pytest 9.2:
```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_e2e_integration.py -v
```
**Outcome**:
- `48 passed, 23 skipped in 19.11s`
- Exit code: `0`
- Zero unexpected test activations
- Zero regressions across existing tests

Full suite regression baseline:
- Pre-existing tests: 135 passed
- Integration test suite: 48 passed, 23 skipped
- Total: **183 passed, 23 skipped** (exit code 0)

---

## 4. Exact Implementation Specification for Worker M5.1 Iteration 2

### 4.1 Edit 1: Fix `is_route_mounted` Router Traversal

- **File**: `backend/tests/test_e2e_integration.py`
- **Location**: Lines 62–73
- **Operation**: Replace `is_route_mounted` definition

#### Target Content (Lines 62–73):
```python
def is_route_mounted(path: str, method: str = "GET") -> bool:
    """Helper to detect whether an endpoint route is registered in the FastAPI app."""
    for route in app.routes:
        r_path = getattr(route, "path", None)
        methods = getattr(route, "methods", [])
        if r_path == path and method in methods:
            return True
        if r_path:
            pattern = re.sub(r"\{[a-zA-Z0-9_]+\}", "[^/]+", r_path)
            if re.fullmatch(pattern, path) and method in methods:
                return True
    return False
```

#### Replacement Content:
```python
def is_route_mounted(path: str, method: str = "GET") -> bool:
    """Helper to detect whether an endpoint route is registered in the FastAPI app."""
    candidates = []
    for route in app.routes:
        if hasattr(route, "effective_candidates"):
            candidates.extend(route.effective_candidates())
        else:
            candidates.append(route)

    for route in candidates:
        r_path = getattr(route, "path", None)
        methods = getattr(route, "methods", [])
        if r_path == path and method in methods:
            return True
        if r_path:
            pattern = re.sub(r"\{[a-zA-Z0-9_]+\}", "[^/]+", r_path)
            if re.fullmatch(pattern, path) and method in methods:
                return True
    return False
```

### 4.2 Edit 2: Fix Test Name Typo for R5-04

- **File**: `backend/tests/test_e2e_integration.py`
- **Location**: Line 1174
- **Operation**: Rename test function to match R5-04 requirement

#### Target Content (Line 1174):
```python
def test_t1_r2_04_reconciliation_comparison_csv_export(e2e_tokens):
```

#### Replacement Content:
```python
def test_t1_r5_04_reconciliation_comparison_csv_export(e2e_tokens):
```

### 4.3 Unified Diff Patch

```patch
--- a/backend/tests/test_e2e_integration.py
+++ b/backend/tests/test_e2e_integration.py
@@ -62,7 +62,13 @@ client = TestClient(app)
 def is_route_mounted(path: str, method: str = "GET") -> bool:
     """Helper to detect whether an endpoint route is registered in the FastAPI app."""
+    candidates = []
     for route in app.routes:
+        if hasattr(route, "effective_candidates"):
+            candidates.extend(route.effective_candidates())
+        else:
+            candidates.append(route)
+
+    for route in candidates:
         r_path = getattr(route, "path", None)
         methods = getattr(route, "methods", [])
         if r_path == path and method in methods:
@@ -1174,3 +1180,3 @@ def test_t1_r5_03_snapshot_roster_csv_export_streaming(e2e_tokens):
-def test_t1_r2_04_reconciliation_comparison_csv_export(e2e_tokens):
+def test_t1_r5_04_reconciliation_comparison_csv_export(e2e_tokens):
     """R5-04: Comparison report CSV export includes classifications and summary block."""
```

---

## 5. Worker Verification Commands

Worker M5.1 Iteration 2 must execute the following commands in sequence:

1. **Verify Route Probing on Mounted vs. Unmounted Routes**:
   ```cmd
   cmd /c "set PYTHONPATH=backend&& .\backend\venv\Scripts\python.exe -c ""from tests.test_e2e_integration import is_route_mounted; assert is_route_mounted('/api/v1/auth/login', 'POST') is True; assert is_route_mounted('/api/v1/reconciliation/runs', 'POST') is True; assert is_route_mounted('/api/v1/reconciliation/unified', 'POST') is False; print('ROUTE_PROBE_SUCCESS')"""
   ```
   *Expected Output*: `ROUTE_PROBE_SUCCESS` with exit code `0`.

2. **Verify E2E Test Suite Execution**:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_e2e_integration.py -v
   ```
   *Expected Output*: `48 passed, 23 skipped in ~19s` with exit code `0`.

3. **Verify R5-04 Renamed Test Execution**:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/test_e2e_integration.py -k test_t1_r5_04_reconciliation_comparison_csv_export -v
   ```
   *Expected Output*: `1 passed, 70 deselected in ~4s` with exit code `0`.

4. **Verify Complete Backend Regression Suite**:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
   ```
   *Expected Output*: `183 passed, 23 skipped in ~80s` with exit code `0`.

5. **Verify Frontend Build**:
   ```cmd
   cmd /c npm run build
   ```
   *Expected Output*: `✓ built in ~3s` with exit code `0`.

6. **Verify Git Hygiene**:
   ```powershell
   git diff --check
   ```
   *Expected Output*: Clean exit code `0`.
