# Deep-Dive Analysis: Skipped Progressive Tests and Route Contract Alignment

**Author:** Explorer M5.1-It2-2 (`teamwork_explorer`)  
**Target File:** `backend/tests/test_e2e_integration.py`  
**Reference Specs:** `PROJECT.md`, `API_CONTRACTS.md`, `TEST_INFRA.md`, `ORIGINAL_REQUEST.md`  
**Date:** 2026-10-30T21:14:00Z  

---

## 1. Executive Summary

This investigation analyzed all 71 tests in `backend/tests/test_e2e_integration.py`, with special focus on the **23 progressive tests currently skipped via `pytest.skip`**.

### Key Findings
1. **Perfect Route & Contract Alignment**: All 23 skipped tests probe exactly 5 planned endpoints across Milestones M5.2, M5.3, and M5.4. Every probed path, HTTP method, parameter format (`{token}`, `?academic_year`, UUIDs), and response contract matches `PROJECT.md` with **100% fidelity**.
2. **Root Cause of Permanent Skip (`is_route_mounted`)**: In `backend/tests/test_e2e_integration.py:62–73`, `is_route_mounted` iterates over `app.routes`. In FastAPI 0.115+, routers mounted via `app.include_router(..., prefix="/api/v1")` are stored as `fastapi.routing._IncludedRouter` instances where `getattr(route, "path", None)` is always `None`. As a result, `is_route_mounted` evaluates to `False` even for valid, mounted endpoints under `/api/v1` (e.g. `is_route_mounted('/api/v1/auth/login', 'POST') == False`). Without fixing `is_route_mounted`, the 23 progressive tests will remain permanently skipped even after M5.2, M5.3, and M5.4 endpoints are implemented.
3. **Line 1174 Typo Confirmed**: At line 1174, `test_t1_r2_04_reconciliation_comparison_csv_export` incorrectly re-uses the `test_t1_r2_04_` prefix from Workstream 2 (already declared at line 557). Its docstring specifies `R5-04: Comparison report CSV export...`, and it is nested sequentially between `test_t1_r5_03` and `test_t1_r5_05`. It must be renamed to `test_t1_r5_04_reconciliation_comparison_csv_export`.

---

## 2. Complete Inventory of All 23 Skipped Progressive Tests

The table below catalogs every skipped test in `backend/tests/test_e2e_integration.py`, its target milestone, probed route, HTTP method, parameter formats, and alignment with `PROJECT.md`.

| # | Test Function Name | Line Range | Workstream | Milestone | Probed Route | Probed Method | Parameter Formats | PROJECT.md Contract Match |
|---|--------------------|------------|------------|-----------|--------------|---------------|-------------------|---------------------------|
| 1 | `test_t1_r2_03_unified_reconciliation_pipeline_joint_execution` | 534–555 | R2 | M5.2 | `/api/v1/reconciliation/unified` | POST | Body: `{"snapshot_id": UUID}` | **PERFECT MATCH** |
| 2 | `test_t1_r2_04_cross_institution_duplicate_detection_by_blind_index` | 557–570 | R2 | M5.2 | `/api/v1/reconciliation/duplicates` | GET | Query: `?academic_year=str` | **PERFECT MATCH** |
| 3 | `test_t2_r2_04_duplicate_detection_ignores_non_concurrent_years` | 693–705 | R2 | M5.2 | `/api/v1/reconciliation/duplicates` | GET | Query: `?academic_year=str` | **PERFECT MATCH** |
| 4 | `test_t1_r4_01_third_party_verifier_request_returns_verified_status` | 963–980 | R4 | M5.3 | `/api/v1/verification/request` | POST | Body: `{"apaar_id": str, "stated_purpose": str, "consent_confirmed": bool}` | **PERFECT MATCH** |
| 5 | `test_t1_r4_02_minimal_field_disclosure_whitelist_enforced` | 982–1005 | R4 | M5.3 | `/api/v1/verification/request` | POST | Body: `{"apaar_id": str, ...}` | **PERFECT MATCH** |
| 6 | `test_t1_r4_03_authenticable_token_and_qr_payload_generation` | 1007–1026 | R4 | M5.3 | `/api/v1/verification/request` | POST | Body: `{"apaar_id": str, ...}` | **PERFECT MATCH** |
| 7 | `test_t1_r4_04_qr_verification_endpoint_validates_token` | 1028–1035 | R4 | M5.3 | `/api/v1/verification/qr/{token}` | GET | Path: `{token}` | **PERFECT MATCH** |
| 8 | `test_t1_r4_05_verification_purpose_ledger_audit_logging` | 1037–1047 | R4 | M5.3 | `/api/v1/verification/request` | POST | Body: `{"apaar_id": str, ...}` | **PERFECT MATCH** |
| 9 | `test_t2_r4_01_missing_consent_confirmation_rejected` | 1051–1067 | R4 | M5.3 | `/api/v1/verification/request` | POST | Body: `{"consent_confirmed": false}` | **PERFECT MATCH** |
| 10 | `test_t2_r4_02_non_existent_apaar_returns_not_found` | 1069–1087 | R4 | M5.3 | `/api/v1/verification/request` | POST | Body: `{"apaar_id": "000000000000"}` | **PERFECT MATCH** |
| 11 | `test_t2_r4_03_tampered_or_expired_qr_token_returns_invalid` | 1089–1098 | R4 | M5.3 | `/api/v1/verification/qr/{token}` | GET | Path: `{token}` | **PERFECT MATCH** |
| 12 | `test_t2_r4_04_unauthenticated_or_unauthorised_verification_blocked` | 1100–1110 | R4 | M5.3 | `/api/v1/verification/request` | POST | Headers: none (unauthenticated) | **PERFECT MATCH** |
| 13 | `test_t2_r4_05_blank_or_whitespace_purpose_rejected` | 1112–1124 | R4 | M5.3 | `/api/v1/verification/request` | POST | Body: `{"stated_purpose": "   "}` | **PERFECT MATCH** |
| 14 | `test_t1_r5_01_institution_admin_dashboard_summary_scoped` | 1132–1143 | R5 | M5.4 | `/api/v1/dashboard/summary` | GET | Headers: `Bearer <inst_admin>` | **PERFECT MATCH** |
| 15 | `test_t1_r5_02_regulatory_reviewer_dashboard_summary_system_wide` | 1145–1156 | R5 | M5.4 | `/api/v1/dashboard/summary` | GET | Headers: `Bearer <reviewer>` | **PERFECT MATCH** |
| 16 | `test_t2_r5_01_institution_admin_cannot_query_foreign_dashboard` | 1210–1222 | R5 | M5.4 | `/api/v1/dashboard/summary` | GET | Query: `?institution_id=UUID` | **PERFECT MATCH** |
| 17 | `test_t2_r5_04_empty_programme_dashboard_zero_division_safety` | 1253–1261 | R5 | M5.4 | `/api/v1/dashboard/summary` | GET | Headers: `Bearer <token>` | **PERFECT MATCH** |
| 18 | `test_t2_r5_05_unauthenticated_dashboard_access_returns_401` | 1263–1270 | R5 | M5.4 | `/api/v1/dashboard/summary` | GET | Headers: none (unauthenticated) | **PERFECT MATCH** |
| 19 | `test_t1_r6_04_cross_institution_duplicate_flagged_in_unified_run` | 1305–1313 | R6 | M5.2 | `/api/v1/reconciliation/duplicates` | GET | Headers: `Bearer <reviewer>` | **PERFECT MATCH** |
| 20 | `test_t3_cross_02_discrepancy_resolution_reflects_in_dashboard_kpis` | 1472–1480 | Cross | M5.4 | `/api/v1/dashboard/summary` | GET | Headers: `Bearer <reviewer>` | **PERFECT MATCH** |
| 21 | `test_t3_cross_03_submission_confirmation_enables_immediate_third_party_verification` | 1482–1502 | Cross | M5.3 | `/api/v1/verification/request` | POST | Body: confirmed student APAAR | **PERFECT MATCH** |
| 22 | `test_t3_cross_05_verification_privacy_whitelisting_under_active_discrepancy` | 1519–1533 | Cross | M5.3 | `/api/v1/verification/request` | POST | Body: `{"apaar_id": str, ...}` | **PERFECT MATCH** |
| 23 | `test_t4_scenario_4_external_verifier_purpose_stated_request_and_qr_check` | 1638–1658 | Scenario | M5.3 | `/api/v1/verification/request` & `/qr/{token}` | POST / GET | Full Journey + `{token}` check | **PERFECT MATCH** |

---

## 3. Milestone-by-Milestone Verification

### 3.1 Milestone 5.2: Unified Reconciliation & Duplicate Detection (4 tests)

#### Planned Endpoints in `PROJECT.md` (Lines 51–57)
- **Endpoint**: `POST /api/v1/reconciliation/unified`
  - Input: `{"snapshot_id": UUID, "approval_config_id": UUID (optional)}`
  - Output: `{"reconciliation_run_id": UUID, "cohort_summary": {...}, "intake_summary": {...}, "duplicate_candidates": [...]}`
- **Endpoint**: `GET /api/v1/reconciliation/duplicates`
  - Input: `?academic_year=2024-2025`
  - Output: `List[DuplicateCandidateResponse]`

#### Verification Against Tests:
1. **`test_t1_r2_03_unified_reconciliation_pipeline_joint_execution` (Lines 534–555)**:
   - Probes: `is_route_mounted("/api/v1/reconciliation/unified", "POST")`
   - Request: `POST /api/v1/reconciliation/unified` with `{"snapshot_id": snap_id}`
   - Asserts: status `200`, presence of keys: `"reconciliation_run_id"`, `"cohort_summary"`, `"intake_summary"`, `"duplicate_candidates"`.
   - **Status**: 100% Contract Match.

2. **`test_t1_r2_04_cross_institution_duplicate_detection_by_blind_index` (Lines 557–570)**:
   - Probes: `is_route_mounted("/api/v1/reconciliation/duplicates", "GET")`
   - Request: `GET /api/v1/reconciliation/duplicates?academic_year=2024-25`
   - Asserts: status `200`, response is `list`.
   - **Status**: 100% Contract Match.

3. **`test_t2_r2_04_duplicate_detection_ignores_non_concurrent_years` (Lines 693–705)**:
   - Probes: `is_route_mounted("/api/v1/reconciliation/duplicates", "GET")`
   - Request: `GET /api/v1/reconciliation/duplicates?academic_year=2024-25`
   - Asserts: status `200`.
   - **Status**: 100% Contract Match.

4. **`test_t1_r6_04_cross_institution_duplicate_flagged_in_unified_run` (Lines 1305–1313)**:
   - Probes: `is_route_mounted("/api/v1/reconciliation/duplicates", "GET")`
   - Request: `GET /api/v1/reconciliation/duplicates`
   - Asserts: status `200`.
   - **Status**: 100% Contract Match.

---

### 3.2 Milestone 5.3: Authorised Verification & Privacy Portal (13 tests)

#### Planned Endpoints in `PROJECT.md` (Lines 59–65)
- **Endpoint**: `POST /api/v1/verification/request`
  - Headers: `Authorization: Bearer <jwt_student_verifier>`
  - Input: `{"apaar_id": str, "stated_purpose": str, "consent_confirmed": bool}`
  - Output: `{"verification_id": UUID, "status": "VERIFIED" | "NOT_FOUND", "disclosed_record": {"masked_apaar": "XXXX-XXXX-1234", "masked_name": "A**** K****", "programme_name": str, "institution_name": str, "academic_year": str, "enrolment_status": str}, "token": str, "qr_payload": str}`
- **Endpoint**: `GET /api/v1/verification/qr/{token}`
  - Output: `{"valid": bool, "issued_at": str, "record": {...}}`

#### Verification Against Tests:
1. **Route Probing & Parameter Format**:
   - `is_route_mounted("/api/v1/verification/request", "POST")` probes the request endpoint.
   - `is_route_mounted("/api/v1/verification/qr/{token}", "GET")` probes the QR verification endpoint using the `{token}` path parameter.
   - In lines 1033, 1094, and 1656, concrete calls use `f"/api/v1/verification/qr/{token}"` or sample token strings.
2. **Privacy Whitelist Invariants**:
   - `test_t1_r4_02` strictly asserts that `masked_apaar` is not pure digits (e.g., `XXXX-XXXX-1234`), and that private PII (`date_of_birth`, `father_name`) is excluded from `disclosed_record`.
   - `test_t3_cross_05` asserts that internal regulatory state (`discrepancy_case`) is never leaked to external verifiers.
3. **Security & Validation Invariants**:
   - `test_t2_r4_01`: Missing consent (`consent_confirmed: False`) returns `400 Bad Request`.
   - `test_t2_r4_02`: Unknown APAAR returns `NOT_FOUND` (`status_code` in `[200, 404]`).
   - `test_t2_r4_03`: Tampered token returns `valid: False` (`status_code` in `[200, 404]`).
   - `test_t2_r4_04`: Unauthenticated request returns `401 Unauthorized`.
   - `test_t2_r4_05`: Whitespace-only purpose returns `400` or `422`.
4. **Audit Logging**:
   - `test_t1_r4_05`: Confirms `AuditEvent` records with `event_type.like("%VERIFICATION%")` are populated in the immutable audit ledger.
   - **Status**: 100% Contract Match across all 13 tests.

---

### 3.3 Milestone 5.4: Submissions UI, Dashboard Metrics & Reports (6 tests)

#### Planned Endpoints in `PROJECT.md` (Lines 67–73)
- **Endpoint**: `GET /api/v1/dashboard/summary`
  - Headers: `Authorization: Bearer <jwt>`
  - Output: Role-scoped counts for `INSTITUTION_ADMIN` (own enrolled students, approved intake, utilization %, open discrepancies, pending submissions) and `REGULATORY_REVIEWER` / `SYSTEM_ADMIN` (total institutions, total students across institutions, intake compliance %, total open discrepancy cases).

#### Verification Against Tests:
1. **`test_t1_r5_01` & `test_t1_r5_02`**: Verify role-based dashboard scoping for `INSTITUTION_ADMIN` and `REGULATORY_REVIEWER`.
2. **`test_t2_r5_01`**: Verifies tenant isolation: an `INSTITUTION_ADMIN` querying `?institution_id={foreign_id}` is auto-scoped to own institution or rejected with `403 Forbidden`.
3. **`test_t2_r5_04`**: Verifies zero-division resilience when an institution has 0 enrolled students.
4. **`test_t2_r5_05`**: Verifies `401 Unauthorized` for unauthenticated requests.
5. **`test_t3_cross_02`**: Verifies cross-feature consistency: discrepancy resolution updates the open cases KPI.
6. **Existing Export Endpoints**:
   - Note: Roster and comparison CSV exports (`/api/v1/snapshots/{id}/export` and `/api/v1/snapshots/{id}/compare/export`) are **already mounted and passing** in `backend/tests/test_e2e_integration.py` (`test_t1_r5_03`, `test_t1_r5_05`, `test_t2_r5_02`, `test_t2_r5_03`).
   - M5.4 will enhance `export_service.py` with reproducible PDF exports.
   - **Status**: 100% Contract Match across all 6 tests.

---

## 4. Adversarial Analysis: The `is_route_mounted` Defect

### Current Implementation (`backend/tests/test_e2e_integration.py:62–73`)
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

### Empirical Failure Analysis
FastAPI 0.115+ wraps routers mounted with prefixes into `_IncludedRouter` instances:
```python
[('Route', '/openapi.json', {'GET', 'HEAD'}),
 ('Route', '/docs', {'GET', 'HEAD'}),
 ('Route', '/docs/oauth2-redirect', {'GET', 'HEAD'}),
 ('Route', '/redoc', {'GET', 'HEAD'}),
 ('APIRoute', '/health', {'GET'}),
 ('_IncludedRouter', None, None),  # auth router
 ('_IncludedRouter', None, None),  # institutions router
 ('_IncludedRouter', None, None),  # students router
 ('_IncludedRouter', None, None),  # submissions router
 ('_IncludedRouter', None, None),  # snapshots router
 ('_IncludedRouter', None, None),  # reconciliation router
 ('_IncludedRouter', None, None),  # discrepancies router
 ('_IncludedRouter', None, None)]  # approvals router
```
When `is_route_mounted` executes:
- For `/health`: `route.path == '/health'`, returns `True`.
- For `/api/v1/auth/login`: `route.path` on all `_IncludedRouter` objects is `None`. It returns `False`!
- For `/api/v1/submissions/upload`: returns `False`!

### Verified Fix
A robust, recursive router traversal handles `_IncludedRouter`, prefixes, and path parameter regex templates (`{token}`, `{institution_id}`, etc.):

```python
def is_route_mounted(path: str, method: str = "GET") -> bool:
    """Helper to detect whether an endpoint route is registered in the FastAPI app."""
    def check_router(router, prefix: str = "") -> bool:
        for route in getattr(router, "routes", []):
            if hasattr(route, "path") and hasattr(route, "methods"):
                full_path = prefix + route.path
                methods = route.methods or []
                if method.upper() in [m.upper() for m in methods]:
                    if full_path == path:
                        return True
                    # Check regex pattern matching when route has {param} template
                    pattern_route = re.sub(r"\{[a-zA-Z0-9_]+\}", "[^/]+", full_path)
                    if re.fullmatch(pattern_route, path):
                        return True
                    # Check regex pattern matching when query path has {param} template
                    pattern_query = re.sub(r"\{[a-zA-Z0-9_]+\}", "[^/]+", path)
                    if re.fullmatch(pattern_query, full_path):
                        return True
            elif hasattr(route, "original_router") and hasattr(route, "include_context"):
                p = prefix + getattr(route.include_context, "prefix", "")
                if check_router(route.original_router, p):
                    return True
            elif hasattr(route, "routes"):
                if check_router(route, prefix):
                    return True
        return False

    return check_router(app)
```

**Verification Results of the Fix**:
```python
is_route_mounted('/api/v1/auth/login', 'POST') -> True
is_route_mounted('/api/v1/auth/login', 'GET') -> False
is_route_mounted('/api/v1/institutions/{institution_id}', 'GET') -> True
is_route_mounted('/api/v1/institutions/test-uuid-1234', 'GET') -> True
is_route_mounted('/health', 'GET') -> True
is_route_mounted('/api/v1/reconciliation/unified', 'POST') -> False  # Correctly False until M5.2
is_route_mounted('/api/v1/verification/qr/{token}', 'GET') -> False  # Correctly False until M5.3
```

---

## 5. Investigation of Line 1174 Typo

### Code Snippet (`backend/tests/test_e2e_integration.py:1173–1188`)
```python
# Line 1174:
def test_t1_r2_04_reconciliation_comparison_csv_export(e2e_tokens):
    """R5-04: Comparison report CSV export includes classifications and summary block."""
    apex = e2e_tokens["apex"]
    ay = f"2024-e2e-{uuid.uuid4().hex[:4]}"
    rows = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", "Cmp Std", f"99{random.randint(1000000000, 9999999999)}", "ACTIVE"]]
    _, snap_id = upload_preview_and_confirm(apex["token"], apex["prog_id"], rows, mark_authoritative=False, academic_year=ay)

    res = client.get(
        f"/api/v1/snapshots/{snap_id}/compare/export?format=csv",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
```

### Observation and Root Cause:
1. At line 557, `test_t1_r2_04_cross_institution_duplicate_detection_by_blind_index` is defined under Workstream 2 (R2-04).
2. At line 1174, under `# Workstream 5: Regulatory Dashboards & Reproducible Multi-Format Export (R5)`, the function was erroneously copied as `test_t1_r2_04_reconciliation_comparison_csv_export`.
3. The surrounding tests in Workstream 5 Tier 1 are:
   - Line 1132: `test_t1_r5_01_institution_admin_dashboard_summary_scoped`
   - Line 1145: `test_t1_r5_02_regulatory_reviewer_dashboard_summary_system_wide`
   - Line 1158: `test_t1_r5_03_snapshot_roster_csv_export_streaming`
   - Line 1174: `test_t1_r2_04_reconciliation_comparison_csv_export` (**MISNAMED**)
   - Line 1189: `test_t1_r5_05_reproducible_export_with_tamper_evident_snapshot_hash`
4. The docstring at line 1175 explicitly states `"""R5-04: Comparison report CSV export includes classifications and summary block."""`.
5. Renaming to `test_t1_r5_04_reconciliation_comparison_csv_export` restores sequential consistency and eliminates the naming clash.

---

## 6. Recommendations for Implementation in M5.1 Iteration 2

1. **Update `is_route_mounted`** in `backend/tests/test_e2e_integration.py` (lines 62–73) using the recursive traversal shown in Section 4.
2. **Rename test function** at line 1174 to `test_t1_r5_04_reconciliation_comparison_csv_export`.
3. **No Changes Needed to Test Logic**: All assertions, payloads, and parameter formats in the 23 skipped tests are already in 100% compliance with `PROJECT.md`. When Worker M5.2 implements `/api/v1/reconciliation/unified` and `/duplicates`, Worker M5.3 implements `/api/v1/verification/request` and `/qr/{token}`, and Worker M5.4 implements `/api/v1/dashboard/summary`, the tests will activate dynamically and cleanly validate the implementation.
