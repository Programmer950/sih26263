# End-to-End Integration Test Suite Architecture & Blueprint
**Target File**: `backend/tests/test_e2e_integration.py`  
**Milestone**: M5.1 — E2E Test Suite Harness  
**Author**: Explorer M5.1 - 3 (E2E Test Suite Architect)  
**Date**: 2026-10-30  

---

## 1. Executive Summary & Objective

The objective of `test_e2e_integration.py` is to establish an opaque-box, requirement-driven, multi-tier integration test harness that validates the complete end-to-end user journeys and cross-module integrity of the **APAAR SETU** platform across all six core workstreams:
- **R1: Institutional Submission Pipeline** (Upload → Mapping → Preview → Atomic Confirm → Snapshot Promotion)
- **R2: Unified Reconciliation & Cross-Institution Duplicate Detection** (Cohort Transition $R(t) \leftrightarrow R(t+1)$, Quota Verification, Blind Index Matching)
- **R3: Discrepancy Lifecycle & Append-Only Regulatory Decisions** (Case Generation Policy, Dossiers, State Machine, Immutable Decision History)
- **R4: Authorised Student Verification** (Purpose Ledger, Consent Gate, Whitelist Disclosure, Masked APAAR `XXXX-XXXX-1234`, Authenticable QR Linkage)
- **R5: Regulatory Dashboards & Reproducible Multi-Format Export** (Aggregated Summaries, Formula Injection Defusing, Cryptographic Snapshot Hashes)
- **R6: Synthetic Multi-Institution Demonstration Flow** (Multi-institution, multi-programme, multi-year longitudinal transitions with documented edge cases)

The test suite enforces a **4-Tier Testing Methodology** (Coverage, Boundary/Negative, Cross-Feature Pairwise, Real-World Scenarios) delivering **71 total test cases**, while preserving 100% regression stability on the existing 135 passing backend tests.

---

## 2. Existing Test Infrastructure Analysis

### 2.1 File Organization & Tooling
- **Virtual Environment**: Python 3.13.9 located at `backend/venv/Scripts/python.exe`.
- **Test Runner**: Pytest 9.2.0 configured via `pytest.ini` with warning filters for Starlette/HTTPX deprecations.
- **Database Backend**: Live PostgreSQL on `127.0.0.1:5432` (`apaar_setu`).
- **HTTP Client**: FastAPI `TestClient(app)` from `starlette.testclient`.

### 2.2 Reusable Fixtures & Auth Patterns
Seeded accounts from database seeds:
- `admin@apex.edu.in` / `Apex@12345` (`INSTITUTION_ADMIN` — Apex Institute of Technology)
- `admin@polytechnic.edu.in` / `Poly@12345` (`INSTITUTION_ADMIN` — National Polytechnic College)
- `reviewer@aicte.gov.in` / `Reviewer@12345` (`REGULATORY_REVIEWER` — AICTE)
- `sysadmin@aicte.gov.in` / `Admin@12345` (`SYSTEM_ADMIN` — AICTE)
- `verifier@tcs.com` / `Verifier@12345` (`THIRD_PARTY_VERIFIER` — Tata Consultancy Services)

Existing test files (e.g. `test_milestone_4_approval_engine.py`, `test_phase_3e_discrepancies.py`) establish auth tokens via:
```python
client.post("/api/v1/auth/login", json={"email": "...", "password": "..."})
```
Returning JWT access tokens passed via header: `{"Authorization": f"Bearer {token}"}`.

### 2.3 Database Sessions & Transaction Management
- Direct SQLAlchemy sessions: `from app.core.database import SessionLocal`
- Standard pattern:
  ```python
  with SessionLocal() as db:
      # Queries and assertions
  ```

### 2.4 Existing Baseline Status & Isolation Root Causes
During initial regression run:
- **Total Existing Tests**: 135 tests.
- **Current Status**: 133 passing, 2 failing.
- **Failure 1**: `test_milestone_4_approval_engine.py::test_multi_tenancy_and_role_guards`  
  - *Root Cause*: Hardcoded `academic_year = "2024-cross-01"` on line 885 violates PostgreSQL unique constraint `uq_active_context_fingerprint` when re-run on persistent database. Assigned to Worker M5.1 - 1.
- **Failure 2**: `test_submissions_phase_3b.py::test_scenario_1_valid_csv_upload_and_preview_zero_student_db_leakage`  
  - *Root Cause*: Database count race condition when executed in non-deterministic sequence with uncommitted test sessions. Passes cleanly in isolated execution (11/11 passed).

### 2.5 Critical Test Isolation Rules for E2E Suite
To prevent test collisions on persistent PostgreSQL:
1. **Dynamic Namespacing**: Every test must generate unique academic years and filenames:
   `academic_year = f"2024-e2e-{uuid.uuid4().hex[:6]}"`
   `filename = f"roster_{uuid.uuid4().hex[:6]}.csv"`
2. **Dynamic APAAR generation**: APAAR identifiers must use unique random digits:
   `apaar = f"99{random.randint(1000000000, 9999999999)}"`
3. **Scoped Counts**: Never assert against unbounded global table counts (`select(func.count(Table.id))`). Always scope count assertions by `institution_id` and `academic_year`.

---

## 3. Progressive Activation Strategy (Staged Milestones)

Because Milestone 5 is implemented progressively across sub-milestones (M5.1 through M5.5):
- **M5.1**: Harness setup & baseline stabilization.
- **M5.2**: `/api/v1/reconciliation/unified` and `/api/v1/reconciliation/duplicates`.
- **M5.3**: `/api/v1/verification/request` and `/api/v1/verification/qr/{token}`.
- **M5.4**: `/api/v1/dashboard/summary` and PDF export.
- **M5.5**: Multi-institution seeders and final demonstration.

The test suite must support **Progressive Capability Detection**:
```python
def is_route_mounted(path: str, method: str = "GET") -> bool:
    """Checks whether an endpoint route is currently registered in FastAPI."""
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", []):
            return True
    return False

skip_if_no_unified = pytest.mark.skipif(
    not is_route_mounted("/api/v1/reconciliation/unified", "POST"),
    reason="Unified reconciliation endpoint scheduled for Milestone 5.2"
)
```
This guarantees that `pytest backend/tests/test_e2e_integration.py -v` exits with code 0 in M5.1 without blocking subsequent workers, and dynamically activates the tests as each feature is delivered.

---

## 4. Complete Test Matrix: Tiers 1–4 across Workstreams R1–R6

| Workstream | Tier 1 (Functional Coverage) | Tier 2 (Boundary & Negative) | Tier 3 (Cross-Feature) | Tier 4 (Real-World Scenarios) | Total Tests |
|---|:---:|:---:|:---:|:---:|:---:|
| **R1: Submissions** | 5 tests | 5 tests | 1 test | Scenario 1 | 12 |
| **R2: Unified Reconciliation** | 5 tests | 5 tests | 1 test | Scenario 2 | 12 |
| **R3: Discrepancy Lifecycle** | 5 tests | 5 tests | 1 test | Scenario 3 | 12 |
| **R4: Authorised Verification** | 5 tests | 5 tests | 1 test | Scenario 4 | 12 |
| **R5: Dashboards & Reports** | 5 tests | 5 tests | 1 test | Scenario 5 | 12 |
| **R6: Demo & Multi-Tenant** | 5 tests | 5 tests | — | Full Walkthrough | 11 |
| **Totals** | **30 tests** | **30 tests** | **5 tests** | **6 tests** | **71 tests** |

---

## 5. Detailed Test Case Blueprint

### 5.1 Workstream 1: Institutional Submission Pipeline (R1)

#### Tier 1: Functional Coverage
1. `test_t1_r1_01_csv_upload_suggests_mapping_and_zero_db_mutations`:
   - POST `/api/v1/submissions/upload` with valid CSV.
   - Assert status 201, `submission_status == "PREVIEW_READY"`.
   - Assert detected headers match CSV, auto-suggested mapping populated.
   - Assert zero rows added to `student_identities` or `roster_snapshots`.
2. `test_t1_r1_02_validation_preview_computes_mapping_hash_and_valid_counts`:
   - POST `/api/v1/submissions/{id}/preview` with column mapping.
   - Assert status 200, SHA-256 `mapping_hash` is 64 hex characters.
   - Assert `valid_rows_count` matches expected valid student count.
3. `test_t1_r1_03_atomic_confirm_promotes_authoritative_roster_snapshot`:
   - POST `/api/v1/submissions/{id}/confirm` with `mark_as_authoritative=True`.
   - Assert status 200, returns valid `snapshot_id`.
   - Query DB: `RosterSnapshot.is_authoritative == True`, `AnnualRosterObservation` rows match headcount.
4. `test_t1_r1_04_submission_list_and_record_pagination_with_status_filter`:
   - GET `/api/v1/submissions` with `submission_status=COMMITTED`.
   - GET `/api/v1/submissions/{id}/records?page=1&limit=10`.
   - Assert pagination metadata (`total`, `page`, `limit`) and correct record rows.
5. `test_t1_r1_05_submission_cancellation_preserves_immutable_audit_trail`:
   - POST `/api/v1/submissions/{id}/cancel`.
   - Assert status 200, `submission_status == "CANCELLED"`.
   - Assert subsequent confirm attempt returns 400 Bad Request.

#### Tier 2: Boundary Value Analysis & Negative Security
6. `test_t2_r1_01_file_size_exceeding_10mb_rejected`:
   - Attempt upload with simulated payload > 10MB (10 * 1024 * 1024 + 1 bytes).
   - Assert status 413 or 400 with `FileSizeExceededError` message.
7. `test_t2_r1_02_zip_bomb_and_path_traversal_archive_rejected`:
   - Upload synthetic ZIP/XLSX archive with compression ratio > 100:1 or directory traversal filenames (`../../evil.xml`).
   - Assert status 400 with `ArchiveSecurityError`.
8. `test_t2_r1_03_missing_mandatory_student_identifier_column_rejected`:
   - POST preview without mapping `student_id` or `full_name`.
   - Assert status 422 or 400 Unprocessable Entity.
9. `test_t2_r1_04_client_idempotency_key_conflict_returns_409`:
   - Upload file with `Idempotency-Key: X`.
   - Re-attempt upload with same `Idempotency-Key: X` but different file content.
   - Assert status 409 Conflict with descriptive detail.
10. `test_t2_r1_05_cross_tenant_upload_attempt_blocked`:
    - Apex Admin uploads with form data `institution_id = polytechnic_id`.
    - Assert status 403 Forbidden ("Tenancy Violation").

---

### 5.2 Workstream 2: Unified Reconciliation & Duplicate Detection (R2)

#### Tier 1: Functional Coverage
11. `test_t1_r2_01_longitudinal_cohort_reconciliation_classifies_trajectories`:
    - POST `/api/v1/reconciliation/runs` with 2023-24 baseline and 2024-25 candidate.
    - Assert classification counts for `CONTINUING`, `ADDED`, and `WITHDRAWN`.
12. `test_t1_r2_02_statutory_intake_reconciliation_evaluates_quotas_and_caps`:
    - POST `/api/v1/approvals/intake/verify` on candidate snapshot.
    - Assert `compliance_status` (COMPLIANT or EXCEPTION_FOUND) and category breakdown.
13. `test_t1_r2_03_unified_reconciliation_pipeline_joint_execution`:
    - POST `/api/v1/reconciliation/unified` with `snapshot_id` and optional `approval_config_id`.
    - Assert response contains `cohort_summary`, `intake_summary`, and `duplicate_candidates`.
14. `test_t1_r2_04_cross_institution_duplicate_detection_by_blind_index`:
    - Seed identical student APAAR blind index in Apex and Polytechnic rosters for same academic year.
    - GET `/api/v1/reconciliation/duplicates?academic_year=...`.
    - Assert duplicate item contains masked APAAR, Institution A name, Institution B name.
15. `test_t1_r2_05_reconciliation_fingerprint_determinism`:
    - Re-run reconciliation on identical candidate and baseline snapshots.
    - Assert `result_fingerprint` matches previous run exactly.

#### Tier 2: Boundary Value Analysis & Negative Security
16. `test_t2_r2_01_self_comparison_as_baseline_rejected`:
    - Execute reconciliation run where `baseline_snapshot_id == candidate_snapshot_id`.
    - Assert status 400 Bad Request.
17. `test_t2_r2_02_sanctioned_intake_boundary_n_vs_n_plus_1`:
    - Create approval config with approved_intake = 60.
    - Verify snapshot with 60 students -> COMPLIANT.
    - Verify snapshot with 61 students -> EXCEPTION_FOUND with regular_variance = +1.
18. `test_t2_r2_03_supernumerary_tfw_five_percent_rounding_boundary`:
    - Approved intake = 60 (5% cap = 3.0). Enrolled TFW = 3 -> COMPLIANT.
    - Enrolled TFW = 4 -> EXCEPTION_FOUND.
19. `test_t2_r2_04_duplicate_detection_ignores_non_concurrent_years`:
    - Student active in Apex in 2023-24 and Polytechnic in 2024-25 (legitimate transfer).
    - Query duplicate detection for 2024-25.
    - Assert student is NOT flagged as concurrent duplicate.
20. `test_t2_r2_05_cross_tenant_reconciliation_run_query_blocked`:
    - Polytechnic Admin queries `/api/v1/reconciliation/runs/{apex_run_id}`.
    - Assert status 403 Forbidden ("Tenancy Violation").

---

### 5.3 Workstream 3: Discrepancy Lifecycle & Append-Only Decisions (R3)

#### Tier 1: Functional Coverage
21. `test_t1_r3_01_case_creation_policy_filters_benign_findings`:
    - Execute reconciliation run with CONTINUING, ADDED, and UNEXPLAINED_APPEARANCE.
    - Assert DiscrepancyCase is created ONLY for UNEXPLAINED_APPEARANCE.
22. `test_t1_r3_02_discrepancy_case_dossier_contains_side_by_side_evidence`:
    - GET `/api/v1/discrepancies/cases/{id}`.
    - Assert dossier contains candidate observation, baseline observation, and provenance metadata.
23. `test_t1_r3_03_institutional_explanation_submission`:
    - Apex Admin submits institutional explanation and evidence references.
    - Assert case status transitions to `EVIDENCE_SUBMITTED` without unauthorized resolution.
24. `test_t1_r3_04_regulatory_reviewer_decision_workflow`:
    - Regulatory Reviewer posts decision `action="ACCEPT_EXCEPTION"`, `to_status="RESOLVED_EXCEPTION"`.
    - Assert case status updated transactionally.
25. `test_t1_r3_05_chronological_append_only_decision_history`:
    - GET `/api/v1/discrepancies/cases/{id}/history`.
    - Assert history preserves all transitions chronologically; verify each decision links to an `audit_event_id`.

#### Tier 2: Boundary Value Analysis & Negative Security
26. `test_t2_r3_01_illegal_status_transition_rejected`:
    - Attempt direct transition from `OPEN` to `RESOLVED` without required review intermediary.
    - Assert status 400 Bad Request ("Invalid state transition").
27. `test_t2_r3_02_mandatory_regulatory_justification_minimum_length`:
    - Regulatory Reviewer posts decision with `mandatory_reason = "ok"` (<10 characters).
    - Assert status 422 or 400 Validation Error.
28. `test_t2_r3_03_request_evidence_cannot_resolve_case`:
    - Reviewer submits decision with `action="REQUEST_EVIDENCE"`, attempting `to_status="RESOLVED"`.
    - Assert transition rejected; case remains in `UNDER_INVESTIGATION`.
29. `test_t2_r3_04_cross_tenant_discrepancy_case_access_blocked`:
    - Apex Admin attempts to view Polytechnic case `/api/v1/discrepancies/cases/{poly_case_id}`.
    - Assert status 403 Forbidden.
30. `test_t2_r3_05_reoccurrence_after_closure_links_prior_case`:
    - Re-run reconciliation on recurring finding after case resolution.
    - Assert new case created with `linked_prior_case_id == prior_case.id` and `occurrence_count == 1`.

---

### 5.4 Workstream 4: Authorised Student Verification & Privacy Portal (R4)

#### Tier 1: Functional Coverage
31. `test_t1_r4_01_third_party_verifier_request_returns_verified_status`:
    - Verifier logs in (`verifier@tcs.com`), calls `POST /api/v1/verification/request` with valid APAAR, stated purpose, and `consent_confirmed=True`.
    - Assert status 200, `status == "VERIFIED"`.
32. `test_t1_r4_02_minimal_field_disclosure_whitelist_enforced`:
    - Assert disclosed record includes: `masked_apaar` (`XXXX-XXXX-1234`), `masked_name` (`A**** K****`), `programme_name`, `institution_name`, `academic_year`, `enrolment_status`.
    - Assert strictly NO disclosure of: unmasked APAAR, date of birth, gender, father/mother name, internal UUID.
33. `test_t1_r4_03_authenticable_token_and_qr_payload_generation`:
    - Assert response includes opaque CSPRNG `token` and base64/JSON `qr_payload`.
34. `test_t1_r4_04_qr_verification_endpoint_validates_token`:
    - GET `/api/v1/verification/qr/{token}`.
    - Assert `valid == True`, `record` matches disclosed fields.
35. `test_t1_r4_05_verification_purpose_ledger_audit_logging`:
    - Query `audit_events` table for verification event.
    - Assert event records verifier user ID, stated purpose, timestamp, and masked student reference.

#### Tier 2: Boundary Value Analysis & Negative Security
36. `test_t2_r4_01_missing_consent_confirmation_rejected`:
    - Submit verification request with `consent_confirmed=False`.
    - Assert status 400 Bad Request ("Consent confirmation is mandatory").
37. `test_t2_r4_02_non_existent_apaar_returns_not_found`:
    - Submit verification request with unseeded APAAR `111122223333`.
    - Assert status 200 with `status == "NOT_FOUND"`, `disclosed_record == None`. Zero DB leakage.
38. `test_t2_r4_03_tampered_or_expired_qr_token_returns_invalid`:
    - GET `/api/v1/verification/qr/invalid-or-tampered-token-123`.
    - Assert status 200 with `valid == False` or 404 Not Found.
39. `test_t2_r4_04_unauthenticated_or_unauthorised_verification_blocked`:
    - Unauthenticated request -> 401 Unauthorized.
    - Institution Admin attempting verifier role endpoint -> 403 Forbidden.
40. `test_t2_r4_05_blank_or_whitespace_purpose_rejected`:
    - Submit verification request with `stated_purpose = "   "`.
    - Assert status 422 or 400 Validation Error.

---

### 5.5 Workstream 5: Regulatory Dashboards & Reproducible Multi-Format Export (R5)

#### Tier 1: Functional Coverage
41. `test_t1_r5_01_institution_admin_dashboard_summary_scoped`:
    - Apex Admin queries `GET /api/v1/dashboard/summary`.
    - Assert returned metrics reflect Apex's enrolled students, approved intake, utilization %, open discrepancies.
42. `test_t1_r5_02_regulatory_reviewer_dashboard_summary_system_wide`:
    - Regulatory Reviewer queries `GET /api/v1/dashboard/summary`.
    - Assert metrics aggregate total institutions, system-wide students, compliance %, total open cases.
43. `test_t1_r5_03_snapshot_roster_csv_export_streaming`:
    - GET `/api/v1/snapshots/{id}/export?format=csv`.
    - Assert Content-Type `text/csv`, header comments contain snapshot metadata, rows match student headcount.
44. `test_t1_r5_04_reconciliation_comparison_csv_export`:
    - GET `/api/v1/snapshots/{id}/export-comparison?format=csv`.
    - Assert CSV includes classification column and summary metrics metadata block.
45. `test_t1_r5_05_reproducible_export_with_tamper_evident_snapshot_hash`:
    - Verify exported report includes `Snapshot Hash` matching `RosterSnapshot.snapshot_hash` and rules version.

#### Tier 2: Boundary Value Analysis & Negative Security
46. `test_t2_r5_01_institution_admin_cannot_query_foreign_dashboard`:
    - Apex Admin calls `GET /api/v1/dashboard/summary?institution_id={poly_id}`.
    - Assert response is auto-scoped to Apex or returns 403 Forbidden.
47. `test_t2_r5_02_formula_injection_vectors_strictly_defused`:
    - Seed student names starting with `=cmd|'/C calc'!A0`, `+HYPERLINK(...)`, `@SUM(...)`.
    - Export snapshot CSV.
    - Assert all malicious prefixes are prepended with single quote (`'=...`, `'+...`, `'@...`).
48. `test_t2_r5_03_non_existent_snapshot_export_returns_404`:
    - GET `/api/v1/snapshots/{random_uuid}/export?format=csv`.
    - Assert status 404 Not Found.
49. `test_t2_r5_04_empty_programme_dashboard_zero_division_safety`:
    - Query dashboard when a programme has 0 enrolled students and 0 intake.
    - Assert utilization % returns `0.0`, no 500 Internal Server Error.
50. `test_t2_r5_05_unauthenticated_dashboard_access_returns_401`:
    - GET `/api/v1/dashboard/summary` without Authorization header.
    - Assert status 401 Unauthorized.

---

### 5.6 Workstream 6: Multi-Institution Synthetic Demonstration Flow (R6)

#### Tier 1: Functional Coverage
51. `test_t1_r6_01_apex_institute_baseline_2023_24_onboarding`:
    - Upload and confirm 2023-24 baseline roster for Apex Institute.
    - Assert authoritative snapshot created with active status.
52. `test_t1_r6_02_apex_institute_candidate_2024_25_cohort_ingestion`:
    - Upload and confirm 2024-25 candidate roster for Apex Institute.
53. `test_t1_r6_03_polytechnic_concurrent_2024_25_ingestion`:
    - Upload and confirm 2024-25 roster for National Polytechnic College.
54. `test_t1_r6_04_cross_institution_duplicate_flagged_in_unified_run`:
    - Execute unified reconciliation run on 2024-25 snapshots.
    - Assert cross-institution duplicate candidate detected between Apex and Polytechnic.
55. `test_t1_r6_05_immutable_audit_ledger_integrity_across_demonstration`:
    - Query `audit_events` for all demonstration transactions.
    - Assert hash chain continuity: `prev_event_hash` correctly links events without broken chains.

#### Tier 2: Boundary Value Analysis & Negative Security
56. `test_t2_r6_01_cross_institution_identity_spoofing_prevented`:
    - Malicious actor attempts to register existing student with altered identity status.
    - Assert blind index match resolves to existing canonical identity.
57. `test_t2_r6_02_ambiguous_identity_flagged_on_conflicting_attributes`:
    - Roster record with identical institution student ID but conflicting date of birth.
    - Assert reconciliation flags `AMBIGUOUS_IDENTITY`.
58. `test_t2_r6_03_missing_approval_configuration_graceful_fallback`:
    - Verify intake compliance on programme with no active approval configuration.
    - Assert result `compliance_status == "INSUFFICIENT_INFORMATION"`, no unhandled exception.
59. `test_t2_r6_04_lateral_entry_segregated_accounting_in_demo_flow`:
    - Roster containing 2nd-year lateral entry students evaluated against separate lateral entry cap.
    - Assert lateral entry students do not consume 1st-year regular sanctioned seats.
60. `test_t2_r6_05_unexplained_disappearance_investigation_dossier`:
    - Student present in baseline 2023-24 but omitted in 2024-25 without documented transfer.
    - Assert flagged as `UNEXPLAINED_DISAPPEARANCE` and case created with priority `HIGH`.

---

### 5.7 Tier 3: Pairwise Combinatorial Cross-Feature Tests

61. `test_t3_cross_01_submission_to_reconciliation_to_discrepancy_pipeline`:
    - Upload candidate roster with intentional intake excess (+2 students) and 1 unexplained appearance.
    - Run unified reconciliation.
    - Assert BOTH intake excess case (programme scope) and student trajectory case (student scope) are generated and cross-linked.
62. `test_t3_cross_02_discrepancy_resolution_reflects_in_dashboard_kpis`:
    - Query initial dashboard open discrepancy count.
    - Regulatory reviewer resolves 1 open case with `ACCEPT_EXCEPTION`.
    - Query dashboard again -> assert open discrepancy count decremented by 1.
63. `test_t3_cross_03_submission_confirmation_enables_immediate_third_party_verification`:
    - Upload & confirm student in snapshot.
    - Verifier immediately calls `/api/v1/verification/request` for that student.
    - Assert instant verification success, masked disclosure, and valid QR token.
64. `test_t3_cross_04_reconciliation_run_generates_reproducible_comparison_report`:
    - Run reconciliation.
    - Stream comparison report CSV.
    - Assert CSV summary numbers match reconciliation run `summary_counts` exactly.
65. `test_t3_cross_05_verification_privacy_whitelisting_under_active_discrepancy`:
    - Query verification for student who is currently under active investigation in a discrepancy case.
    - Assert verification returns standard whitelisted fields without leaking investigation status or discrepancy notes.

---

### 5.8 Tier 4: Real-World Application User Scenarios

66. `test_t4_scenario_1_institutional_upload_to_authoritative_snapshot`:
    - *Persona*: Apex Institution Administrator (`admin@apex.edu.in`).
    - *Journey*: Login → Upload CSV roster for 2024-25 → Inspect column mapping → Confirm preview → Promote to authoritative snapshot.
    - *Assertions*: Snapshot state active, students populated in institutional student records, audit event created.
67. `test_t4_scenario_2_longitudinal_cohort_and_intake_reconciliation`:
    - *Persona*: Institutional Admin & AICTE Reviewer.
    - *Journey*: Baseline 2023-24 vs Candidate 2024-25 unified reconciliation.
    - *Assertions*: Identifies continuing students, documented transfers, evaluates intake quota, generates discrepancy cases for anomalies.
68. `test_t4_scenario_3_discrepancy_dossier_investigation_and_regulatory_decision`:
    - *Persona*: AICTE Regulatory Reviewer (`reviewer@aicte.gov.in`) & Apex Admin.
    - *Journey*: Reviewer lists open cases → Inspects evidence dossier → Requests evidence → Apex Admin submits explanation → Reviewer adjudicates with `ACCEPT_EXCEPTION`.
    - *Assertions*: Append-only decision history, chained audit event, case resolved.
69. `test_t4_scenario_4_external_verifier_purpose_stated_request_and_qr_check`:
    - *Persona*: Third-Party Background Verifier (`verifier@tcs.com`).
    - *Journey*: Login → Submit verification with stated purpose & consent → Receive masked APAAR & token → Verify token via public QR verification endpoint.
    - *Assertions*: Masked APAAR `XXXX-XXXX-1234`, purpose recorded in audit ledger, QR valid.
70. `test_t4_scenario_5_regulatory_dashboard_and_reproducible_export`:
    - *Persona*: AICTE System Administrator (`sysadmin@aicte.gov.in`).
    - *Journey*: Login → Fetch system-wide dashboard summary → Export snapshot and comparison reports in CSV/XLSX.
    - *Assertions*: Accurate aggregated KPIs, defused formula injection, matching snapshot hash.
71. `test_t4_scenario_6_full_multi_institution_demonstration_walkthrough`:
    - *Comprehensive E2E Narrative*: Multi-institution setup (Apex & Polytechnic) → Concurrent rosters with planted duplicate and intake excess → Unified reconciliation flags cross-institution duplicate and quota breach → Employer verifies student record → Regulator resolves discrepancy → Dashboard displays clean final state.

---

## 6. Implementation Blueprint for Worker

### 6.1 Target File Location
`backend/tests/test_e2e_integration.py`

### 6.2 Module Structure & Core Imports
```python
"""End-to-End Integration Test Suite for APAAR SETU Milestone 5 Integration.

Covers Tiers 1-4 across all 6 workstreams:
- R1: Institutional Submission Pipeline
- R2: Unified Reconciliation & Cross-Institution Duplicate Detection
- R3: Discrepancy Lifecycle & Append-Only Regulatory Decisions
- R4: Authorised Student Verification (Masked APAAR, Tokens, QR)
- R5: Regulatory Dashboards & Reproducible Multi-Format Export
- R6: Synthetic Multi-Institution Demonstration Flow

Execution:
    .\\backend\\venv\\Scripts\\python.exe -m pytest backend/tests/test_e2e_integration.py -v
"""

import pytest
import uuid
import random
import io
import csv
from datetime import datetime, date, timezone
from sqlalchemy import select, func, text
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    User,
    Institution,
    Programme,
    RosterSnapshot,
    StudentIdentity,
    InstitutionStudentRecord,
    AnnualRosterObservation,
    AdmissionEpisode,
    TransferEvent,
    ApprovalConfiguration,
    ApprovalCategoryAllocation,
    ReconciliationRun,
    ReconciliationResultItem,
    IntakeReconciliationSummary,
    DiscrepancyCase,
    DiscrepancyCaseDecision,
    AuditEvent,
)
from app.services.storage_service import StorageService

client = TestClient(app)
```

### 6.3 Shared Test Helpers
```python
def is_route_mounted(path: str, method: str = "GET") -> bool:
    """Helper to detect whether an endpoint is registered on FastAPI app."""
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", []):
            return True
    return False

def make_sample_csv(rows: list) -> io.BytesIO:
    """Creates in-memory CSV stream."""
    out = io.StringIO()
    writer = csv.writer(out)
    for r in rows:
        writer.writerow(r)
    return io.BytesIO(out.getvalue().encode("utf-8"))

def submit_preview_and_confirm(
    token: str,
    prog_id: str,
    rows: list,
    academic_year: str,
    mark_authoritative: bool = True,
    submission_type: str = "ANNUAL_ROSTER",
) -> tuple[str, str]:
    """Helper executing upload -> preview -> confirm pipeline."""
    uid = uuid.uuid4().hex[:6]
    file_tuple = (f"e2e_roster_{uid}.csv", make_sample_csv(rows), "text/csv")

    res_up = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": file_tuple},
        data={
            "programme_id": prog_id,
            "academic_year": academic_year,
            "submission_type": submission_type,
        },
    )
    assert res_up.status_code == 201, res_up.text
    sub_id = res_up.json()["submission_id"]

    mapping = {
        "student_id": "student_id",
        "full_name": "full_name",
        "apaar_id": "apaar_id",
        "student_status": "student_status",
    }
    res_prev = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={"column_mapping": mapping},
    )
    assert res_prev.status_code == 200, res_prev.text
    prev_id = res_prev.json()["preview_id"]

    res_conf = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "preview_id": prev_id,
            "column_mapping": mapping,
            "mark_as_authoritative": mark_authoritative,
            "completeness_status": "COMPLETE",
        },
    )
    assert res_conf.status_code == 200, res_conf.text
    return sub_id, res_conf.json()["snapshot_id"]
```

### 6.4 Auth & Context Fixtures
```python
@pytest.fixture(scope="module")
def e2e_tokens():
    """Logs in seeded users and discovers primary programmes."""
    def login(email, pwd):
        r = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        assert r.status_code == 200
        return r.json()["access_token"], r.json()["user"]["institution_id"]

    apex_token, apex_inst_id = login("admin@apex.edu.in", "Apex@12345")
    poly_token, poly_inst_id = login("admin@polytechnic.edu.in", "Poly@12345")
    rev_token, _ = login("reviewer@aicte.gov.in", "Reviewer@12345")
    sys_token, _ = login("sysadmin@aicte.gov.in", "Admin@12345")
    ver_token, _ = login("verifier@tcs.com", "Verifier@12345")

    with SessionLocal() as db:
        apex_prog = db.execute(select(Programme).where(Programme.institution_id == uuid.UUID(apex_inst_id))).scalars().first()
        poly_prog = db.execute(select(Programme).where(Programme.institution_id == uuid.UUID(poly_inst_id))).scalars().first()
        apex_prog_id = str(apex_prog.id) if apex_prog else None
        poly_prog_id = str(poly_prog.id) if poly_prog else None

    return {
        "apex": {"token": apex_token, "inst_id": apex_inst_id, "prog_id": apex_prog_id},
        "poly": {"token": poly_token, "inst_id": poly_inst_id, "prog_id": poly_prog_id},
        "reviewer": {"token": rev_token},
        "sysadmin": {"token": sys_token},
        "verifier": {"token": ver_token},
    }
```

---

## 7. Verification Method & Success Criteria

### 7.1 Targeted E2E Test Suite Execution
```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_e2e_integration.py -v
```
- **Success Criteria**: 0 failures, 0 errors, clean exit code 0.

### 7.2 Full Backend Regression Suite Execution
```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```
- **Success Criteria**: All existing 135 tests pass + all new E2E tests pass cleanly.

### 7.3 Frontend Production Build Check
```powershell
cmd /c npm run build
```
- **Success Criteria**: Clean Vite build exit code 0.
