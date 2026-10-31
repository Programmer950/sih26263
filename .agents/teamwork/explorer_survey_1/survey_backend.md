# Backend Codebase & Database Architecture Comprehensive Survey Report
**Project:** APAAR SETU — Longitudinal Student Data Integrity & Verification Platform  
**Workspace:** `c:\Users\moham\OneDrive\Desktop\SIH26\26263`  
**Investigator:** Explorer 1 (Backend Codebase Investigator)  
**Date:** 2026-10-31  
**Integrity Mode:** Development (Read-Only Analysis)

---

## 1. Executive Summary

A comprehensive, read-only architectural inspection of the `backend/` codebase, Alembic migrations, database models, business logic services, REST API endpoints, and existing pytest test suite was conducted.

### Key Highlights:
1. **Alembic Database Head:** Verified at `0005_approval_intake_matrix (head)`. All 5 migration revisions are cleanly applied against PostgreSQL on `127.0.0.1:5432` (`apaar_setu`).
2. **Pytest Regression Baseline:** 
   - Total test suite size: **135 test cases** collected across 14 test modules.
   - **134 tests pass cleanly** (execution time: ~26.7s).
   - **1 test** (`test_milestone_4_approval_engine.py::test_multi_tenancy_and_role_guards`) exhibits a reproducible failure upon rerun due to an unrandomized, hardcoded academic year (`"2024-cross-01"`) colliding with the database partial unique index `uq_active_context_fingerprint`. When executed on a fresh DB or with unique academic year parametrization (identical to Scenarios 1–8), all 135 tests pass 100%.
3. **Core Architectural Strengths:**
   - Multi-layered cryptography: Argon2id password hashing, AES-256-GCM field-level encryption for APAAR IDs, HMAC-SHA256 blind indexing for identity lookups without decrypting, and SHA-256 cryptographically chained immutable audit logging (`AuditEvent`).
   - Strict multi-tenant isolation via `TenantGuard` and role-based access control (`SYSTEM_ADMIN`, `REGULATORY_REVIEWER`, `INSTITUTION_ADMIN`, `STUDENT_VERIFIER`).
   - Robust transactional workflows with PostgreSQL advisory locks, row-level locks (`SELECT ... FOR UPDATE`), and dual-composite foreign keys for complete provenance lineage.
4. **Key Architectural & Integration Gaps Identified across R1–R6:**
   - **R1 (Submissions):** Ingestion and snapshot pipelines are robust, but lack pre-packaged synthetic CSV/XLSX sample datasets in the repository for seamless demonstration.
   - **R2 (Unified Reconciliation):** Cohort comparison (`/snapshots/{id}/compare` and `/reconciliation/runs`) and statutory intake verification (`/approvals/intake/verify`) currently exist as **two disconnected silos**. Furthermore, cross-institution duplicate enrollment checks across concurrent academic years are not yet evaluated during reconciliation.
   - **R3 (Discrepancy Investigation):** Discrepancy case lifecycle and state machine are fully implemented with append-only decisions. However, file evidence uploads for cases are not yet supported (only JSON metadata references), and newly added intake excess classifications need unified display linkage.
   - **R4 (Authorised Verification):** **Major backend gap.** While the `STUDENT_VERIFIER` role is seeded, there is **no dedicated verification API router**, no verification request ledger with stated purpose and consent tracking, no minimal field disclosure endpoint, and no synthetic certificate/QR verification demonstration service.
   - **R5 (Regulatory Dashboards & Reports):** **Major backend gap.** There are no aggregated backend dashboard summary endpoints for institutions or regulators; the frontend currently hardcodes counts or stitches ad-hoc queries. Furthermore, export capabilities are restricted to CSV/XLSX without reproducible PDF report generation.
   - **R6 (Synthetic Dataset & Seeders):** `seed.py` initializes baseline institutions, users, and 15 sample student identities, but does not seed completed submissions, snapshots, approval category allocations, reconciliation runs, or discrepancy cases.

---

## 2. Backend Architecture & Codebase Map

### 2.1 Directory Structure Overview
```
backend/
├── alembic/
│   ├── versions/
│   │   ├── 0001_initial_foundational_entities.py
│   │   ├── 0002_student_repository.py
│   │   ├── 0003_submissions_and_snapshots.py
│   │   ├── 0004_reconciliation_and_discrepancies.py
│   │   └── 0005_approval_intake_matrix.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── approvals.py          # Milestone 4 Approval & Intake verification API
│   │       ├── auth.py               # Authentication, /me, session revocation
│   │       ├── discrepancies.py      # Discrepancy cases, dossiers, decisions
│   │       ├── institutions.py       # Institutions and Programmes management
│   │       ├── reconciliation.py     # Reconciliation runs and result items
│   │       ├── snapshots.py          # Roster snapshots, promotion, comparison, export
│   │       ├── students.py           # Student repository & longitudinal timeline
│   │       └── submissions.py        # Upload, preview, cancel, confirm ingestion
│   ├── core/
│   │   ├── config.py                 # Pydantic v2 Settings, secret validation
│   │   ├── database.py               # Engine, SessionLocal, get_db dependency
│   │   ├── permissions.py            # get_current_user, require_roles, TenantGuard
│   │   └── security.py               # Argon2id, AES-GCM, HMAC blind index, JWT
│   ├── db/
│   │   └── seed.py                   # Roles, institutions, programmes, users, sample data
│   ├── models/                       # 24 SQLAlchemy declarative models
│   ├── schemas/                      # Pydantic request & response contracts
│   ├── services/                     # 13 core domain business logic services
│   └── main.py                       # FastAPI application factory, CORS, exception handlers
└── tests/                            # 14 test modules (135 tests)
```

### 2.2 Core Infrastructure Components
- **Framework:** FastAPI with Uvicorn.
- **ORM & Database:** SQLAlchemy 2.0 with PostgreSQL Dialect (`psycopg2`), connection pool size 10, max overflow 20, pool pre-ping enabled.
- **Security & Cryptography (`app/core/security.py`):**
  - Passwords: `argon2.PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, type=Type.ID)`.
  - Sensitive Field Encryption: AES-256-GCM with PBKDF2 key derivation (SHA-256, 100,000 iterations), 12-byte random IV, and 16-byte authentication tag.
  - Searchable Encryption: HMAC-SHA256 blind index computed over normalized values using `BLIND_INDEX_KEY`.
  - Session Management: JWT with SHA-256 JTI tracked in `session_revocations` table to enable immediate server-side revocation on logout.

---

## 3. Database Schema & Alembic Migration Lineage

### 3.1 Migration Head Verification
- Execution of `alembic current` confirms: `0005_approval_intake_matrix (head)`.
- Migration lineage:
  1. `0001_initial_foundational_entities`: Core tables (`roles`, `institutions`, `programmes`, `users`, `session_revocations`, `audit_events`).
  2. `0002_student_repository`: Longitudinal student tables (`student_identities`, `institution_student_records`, `admission_episodes`, `annual_roster_observations`, `transfer_events`).
  3. `0003_submissions_and_snapshots`: Submissions and snapshot ledger (`source_submissions`, `submission_previews`, `source_submission_records`, `roster_snapshots`).
  4. `0004_reconciliation_and_discrepancies`: Discrepancy investigation engine (`reconciliation_runs`, `reconciliation_result_items`, `discrepancy_cases`, `discrepancy_case_decisions`).
  5. `0005_approval_intake_matrix`: Statutory approval configurations, quota category allocations (`approval_category_allocations`), and intake reconciliation summaries (`intake_reconciliation_summaries`).

### 3.2 Complete Model Inventory (24 Models)
| Model | Table | Purpose | Primary / Unique Constraints |
|---|---|---|---|
| `Role` | `roles` | System roles & permissions | `PK(id)`, `UQ(role_name)` |
| `User` | `users` | Authenticated actors | `PK(id)`, `UQ(email)` |
| `Institution` | `institutions` | Monitored academic institutions | `PK(id)`, `UQ(institution_code)` |
| `Programme` | `programmes` | Academic branches / degrees | `PK(id)`, `UQ(institution_id, programme_code)` |
| `SessionRevocation` | `session_revocations` | Blacklisted JWT JTI entries | `PK(id)`, `UQ(jti)` |
| `AuditEvent` | `audit_events` | SHA-256 hash-chained event log | `PK(id)`, index on `event_hash` |
| `StudentIdentity` | `student_identities` | Global canonical student identity | `PK(id)`, `UQ(internal_student_uuid)`, `UQ(apaar_blind_index)` |
| `InstitutionStudentRecord` | `institution_student_records` | Institution-scoped enrollment (Roll No) | `PK(id)`, `UQ(institution_id, institution_student_id)` |
| `AdmissionEpisode` | `admission_episodes` | Formal admission record & quotas | `PK(id)`, FK to student, institution, programme |
| `AnnualRosterObservation` | `annual_roster_observations` | Yearly cohort presence & state | `PK(id)`, Dual FK to source submission and record |
| `TransferEvent` | `transfer_events` | Inter-institutional transfer evidence | `PK(id)`, source & dest FKs, status (`DOCUMENTED`) |
| `SourceSubmission` | `source_submissions` | Uploaded roster file metadata | `PK(id)`, `UQ(uq_active_context_fingerprint)` |
| `SubmissionPreview` | `submission_previews` | Hash-bound preview & mapping | `PK(id)`, `mapping_hash`, `is_active` |
| `SourceSubmissionRecord` | `source_submission_records` | Unmutated row-level evidence & formulas | `PK(id)`, FK to `source_submissions` |
| `RosterSnapshot` | `roster_snapshots` | Canonical student cohort snapshot | `PK(id)`, `snapshot_hash`, `is_authoritative` |
| `ReconciliationRun` | `reconciliation_runs` | Immutable cohort comparison run | `PK(id)`, `result_fingerprint`, FKs to snapshots |
| `ReconciliationResultItem`| `reconciliation_result_items` | Student-level reconciliation outcome | `PK(id)`, 8 classifications, FK to case |
| `DiscrepancyCase` | `discrepancy_cases` | Investigation dossier | `PK(id)`, `UQ(case_number)`, nullable student FK |
| `DiscrepancyCaseDecision`| `discrepancy_case_decisions` | Append-only decision record | `PK(id)`, `mandatory_reason`, audit FK |
| `ApprovalConfiguration` | `approval_configurations` | AICTE statutory approval limits | `PK(id)`, `UQ(uq_active_approval_config)`, versioned |
| `ApprovalCategoryAllocation` | `approval_category_allocations` | Quota allocations (TFW, EWS, NRI) | `PK(id)`, `calculated_seat_cap`, rounding method |
| `IntakeReconciliationSummary` | `intake_reconciliation_summaries` | Verified intake comparison results | `PK(id)`, variance metrics, compliance status |

---

## 4. Existing Test Suite Verification (All 135 Tests)

### 4.1 Pytest Execution Summary
The test command `.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v` was executed.
- Total collected tests: **135 items** across 14 test modules.
- **134 tests PASSED** cleanly.
- **1 test FAILED**: `test_milestone_4_approval_engine.py::test_multi_tenancy_and_role_guards`.

### 4.2 Root Cause Analysis of the Single Test Failure
```
FAILED backend/tests/test_milestone_4_approval_engine.py::test_multi_tenancy_and_role_guards
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "uq_active_context_fingerprint"
DETAIL: Key (institution_id, programme_id, academic_year, submission_type, file_fingerprint) = 
  (7ffb378d-9eda-4342-a727-4fb6cbc9b18b, 6b9b9092-0d19-4ee1-94ac-30aa4fd09e24, 2024-cross-01, ANNUAL_ROSTER, 8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92) already exists.
```
- **Observation:** In `test_milestone_4_approval_engine.py`:
  - Scenarios 1–8 generate randomized academic years:
    `ay = f"2024-sc1-{uuid.uuid4().hex[:4]}"` (Line 354)
    `ay = f"2024-sc7-{uuid.uuid4().hex[:4]}"` (Line 761)
    `ay = f"2024-sc8-{uuid.uuid4().hex[:4]}"` (Line 796)
  - However, in `test_multi_tenancy_and_role_guards` (Line 885):
    `apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, "2024-cross-01", students, apex_user.id)`
    The academic year `"2024-cross-01"` is hardcoded!
  - `SourceSubmission` enforces partial unique index `uq_active_context_fingerprint` across `(institution_id, programme_id, academic_year, submission_type, file_fingerprint)` WHERE `submission_status != 'CANCELLED'`.
  - When the test suite was run for the second time on the local persistent Postgres database, the pre-existing row from the prior run triggered a `UniqueViolation`.
- **Targeted 1-Line Fix:** Replace `"2024-cross-01"` on line 885 of `test_milestone_4_approval_engine.py` with `f"2024-cross-{uuid.uuid4().hex[:4]}"`.
- **Clean Run Verification:** Executing `pytest backend/tests/ -k "not test_multi_tenancy_and_role_guards"` confirms **134 passed, 1 deselected in 26.74s**.

### 4.3 Test Module Coverage Breakdown
| Test Module | Tests | Focus Areas |
|---|---|---|
| `test_auth.py` | 7 | Argon2id hashing, blind index determinism, AES-GCM roundtrip, seeded user logins, session revocation, tenant guards |
| `test_database.py` | 5 | PostgreSQL connection, weak secret rejection, foundational entity CRUD, unique constraints, FK rollback |
| `test_institutions.py` | 4 | Multi-tenant institution listing, IDOR protection on institution detail, programme listing with approved intake, RBAC |
| `test_students.py` | 12 | Student repository listing, filtering, tenancy isolation, registration, APAAR format validation, blind indexing, timeline |
| `test_submissions_phase_3a.py` | 8 | Storage service, 10MB limits, SHA-256 fingerprinting, directory traversal protection |
| `test_submissions_phase_3b.py` | 9 | CSV/XLSX parsing, pre-flight preview, duplicate detection, formula preservation, zip bomb rejection |
| `test_submissions_phase_3b_corrective.py` | 14 | MIME validation, transactional cleanup on commit failure, encoding detection (UTF-8 with BOM, Latin-1 fallback) |
| `test_submissions_phase_3c.py` | 20 | Atomic transactional ingestion, repeated APAAR resolution, missing/invalid APAAR handling, rollback safety, concurrency |
| `test_submissions_phase_3c_corrective.py` | 14 | Advisory lock serialization on promotion, failure state machine, version binding, cancellation retention policy |
| `test_snapshots_phase_3d.py` | 15 | Snapshot promotion, supersession, audit chaining, comparison engine (8 classifications), export with CWE-1236 defusing |
| `test_phase_3e_discrepancies.py` | 5 | Reconciliation run results persistence, case creation policy, idempotency, equivalence linking, status transitions |
| `test_phase_3e_independent_audit.py` | 6 | FK restrictions, advisory lock idempotency, case isolation, reopen lineage, cross-tenant isolation, fingerprint determinism |
| `test_milestone_4_approval_engine.py` | 10 | Approval configuration lifecycle & amendment, Scenarios 1–8 (intake excess, supernumerary, sub-quotas, rounding, anti-double counting, lateral entry, safe fallback, precedence), multi-tenancy |
| `test_milestone_4_independent_audit.py` | 6 | Date constraints, immutability & supersession, duplicate records, fractional rounding matrix, status precedence, RBAC |
| **Total** | **135** | **134 passing baseline, 100% passing when academic year collision is resolved** |

---

## 5. Workstream Capability & Gap Mapping (R1 to R6)

### R1. Workstream 1 — End-to-end Institutional Submission
- **Existing Capabilities:**
  - Robust file upload with SHA-256 fingerprinting and 10MB limit (`POST /api/v1/submissions/upload`).
  - Pre-flight preview and header autodetection (`PreviewService.suggest_column_mapping`).
  - Full-file preview and mapping hash binding (`POST /api/v1/submissions/{id}/preview`).
  - Cancellation with evidence retention (`POST /api/v1/submissions/{id}/cancel`).
  - Atomic transactional ingestion (`POST /api/v1/submissions/{id}/confirm` -> `IngestionService.confirm_and_ingest`).
  - Identity resolution with HMAC blind indexing and AES-256-GCM encryption.
  - Annual roster observation recording with dual-composite FKs (`source_submission_id`, `source_record_id`).
  - Authoritative snapshot promotion with advisory lock serialization and SHA-256 audit chaining (`POST /api/v1/snapshots/{id}/promote`).
- **Gaps & Missing Links:**
  - **No Pre-Packaged Synthetic Roster Files:** The repository currently has zero `.csv` or `.xlsx` files. The demo flow requires pre-built sample files ready for upload.
  - **Versioned Correction Submission Flow:** An institution admin correcting a discrepant roster needs an explicit submission workflow that marks the new submission as a correction to a prior submission/case, promoting a new candidate snapshot for re-reconciliation.

### R2. Workstream 2 — Unified Reconciliation
- **Existing Capabilities:**
  - `ComparisonService.compare_snapshots`: Reconciles candidate snapshot against resolved baseline (8 deterministic categories: `ADDED`, `CONTINUING`, `WITHDRAWN`, `DOCUMENTED_TRANSFER`, `UNEXPLAINED_APPEARANCE`, `UNEXPLAINED_DISAPPEARANCE`, `AMBIGUOUS_IDENTITY`, `INSUFFICIENT_EVIDENCE`).
  - `ReconciliationService.execute_run`: Immutable execution, run fingerprinting, result item persistence, and case creation.
  - `IntakeService.verify_intake_for_snapshot`: High-precision regulatory intake reconciliation against approval configuration and category allocations.
- **Gaps & Missing Links:**
  - **Disconnected Endpoints:** Cohort reconciliation (`POST /api/v1/reconciliation/runs`) and Intake verification (`POST /api/v1/approvals/intake/verify`) are separate operations. In a unified regulatory platform, a unified reconciliation execution endpoint should run both cohort comparison and intake verification on the same snapshot, producing a consolidated reconciliation result.
  - **Cross-Institution Duplicate Enrolment Check:** Currently neither `ComparisonService` nor `IntakeService` queries whether a student with the same `StudentIdentity` is concurrently enrolled in another institution for the same academic year! The database schema supports this via `annual_roster_observations` joining `student_identities` across different `institution_id` values, but the reconciliation engine does not query or flag cross-institutional duplicates.

### R3. Workstream 3 — Unified Discrepancy Investigation
- **Existing Capabilities:**
  - `DiscrepancyCase` model supporting both student-level cases (`student_identity_id` populated) and collective intake excess cases (`student_identity_id` is NULL, scoped to programme and academic year).
  - Strict 7-step state machine: `OPEN` -> `UNDER_INVESTIGATION` -> `EVIDENCE_REQUESTED` -> `EXPLANATION_SUBMITTED` -> `VERIFIED_VALID` / `CORRECTION_SUBMITTED` -> `CLOSED` (with `REOPEN_CASE`).
  - Controlled transition validation, role enforcement, mandatory reason check (minimum 10 characters), and append-only `DiscrepancyCaseDecision` history.
  - Full case dossier endpoint (`GET /api/v1/discrepancies/cases/{id}`) returning observations, decisions, and system explanation.
- **Gaps & Missing Links:**
  - **Evidence Document Attachment Endpoint:** The decision table has `evidence_references` JSONB, but there is no endpoint for uploading evidence files (e.g. transfer certificates, NOCs, gazette notifications) directly to a case.
  - **Unified Case Filtering:** Ensure both student-level cohort discrepancies and programme-level intake discrepancies are filterable and seamlessly navigable in the case list.

### R4. Workstream 4 — Authorised Student Verification
- **Existing Capabilities:**
  - `STUDENT_VERIFIER` role seeded in database with permissions `{"verify_student_record": True, "verify_certificate": True}`.
  - Masked APAAR formatting (`XXXX-XXXX-NNNN`) and AES-256-GCM encryption in `IdentityService`.
  - Student timeline reconstruction in `IdentityService.get_student_timeline`.
- **Gaps & Missing Links (Major Backend Gap):**
  - **No Dedicated Verification Router / Service:** `app/api/v1/verification.py` does not exist.
  - **No Verification Request & Audit Ledger:** There is no model or endpoint to record a third-party verifier's request with stated purpose (e.g. "Pre-employment Verification", "Higher Studies Admission"), consent confirmation, and timestamp.
  - **No Minimal Disclosure Endpoint:** Third-party verifiers currently have no endpoint tailored to minimal field disclosure (name, institution, programme, enrollment status, completion year, masked APAAR, verification validity timestamp, verification reference ID). External verifiers must NOT query full student repository endpoints.
  - **No Synthetic Certificate & QR Verification Service:** Missing cryptographic verification token/hash generation and endpoint (`GET /api/v1/verification/verify-certificate/{token}`) for QR code scanning demonstration.

### R5. Workstream 5 — Regulatory Dashboards and Reports
- **Existing Capabilities:**
  - `ExportService.export_snapshot_roster` (CSV/XLSX) and `ExportService.export_comparison_report` (CSV/XLSX).
  - Formula injection defusing (`defuse_formula_injection`, CWE-1236 protection).
- **Gaps & Missing Links (Major Backend Gap):**
  - **No Aggregated Dashboard Endpoints:** Frontend currently hardcodes stats or issues multiple disjointed queries. Needed:
    - Institutional Dashboard Summary (`GET /api/v1/institutions/{id}/dashboard-summary` or `/api/v1/dashboard/institution`): Monitored programmes, approved vs actual intake, submission pipeline status, open discrepancy cases, verification requests.
    - AICTE Central Regulatory Governance Dashboard (`GET /api/v1/dashboard/regulatory`): Nationwide institution count, total enrolled students, intake compliance summary (COMPLIANT, EXCEPTION_FOUND, INSUFFICIENT_INFORMATION), open discrepancy cases by priority, recent audit trail.
  - **Reproducible PDF Regulatory Reports:** There is currently no PDF generator. A PDF export service compiling snapshot provenance, rule versions, engine versions, and regulatory audit trail is needed for statutory compliance reporting.

### R6. Workstream 6 — Demo Dataset & Seeders
- **Existing Capabilities:**
  - `seed.py` creates 4 roles, 3 institutions (Apex, Polytechnic, Kaveri), 3 programmes for Apex, 6 user accounts with fixed passwords, and 15 sample student records.
- **Gaps & Missing Links:**
  - `seed.py` does not create `ApprovalCategoryAllocation` records (TFW, EWS quotas).
  - `seed.py` does not create any committed `SourceSubmission`, `RosterSnapshot`, `ReconciliationRun`, or `DiscrepancyCase`.
  - The repo lacks ready-to-use sample CSV files representing the complete demonstration narrative:
    1. Base roster (2023-24).
    2. Continuing roster (2024-25) containing continuing students, documented transfer, missing APAAR, lateral entry, unexplained appearance, and intake excess.
    3. Corrected roster (2024-25 v2) demonstrating discrepancy resolution and re-reconciliation.

---

## 6. Reusable Services, Repositories, and APIs Catalog

| Service / Module | Key Functions / Methods | Reusability in Integration | Integration Role |
|---|---|---|---|
| `IdentityService` | `validate_apaar_format`, `register_student`, `get_student_timeline` | High (100% reusable) | Identity resolution, masking, and longitudinal trajectory |
| `IngestionService` | `confirm_and_ingest` | High (100% reusable) | Atomic roster ingestion into student repository and candidate snapshot |
| `SnapshotService` | `promote_snapshot`, `execute_authoritative_promotion_core` | High (100% reusable) | Advisory locked authoritative promotion and audit logging |
| `ComparisonService` | `resolve_baseline`, `compare_snapshots`, `_classify_candidate_student` | High (Can be extended with cross-institution check) | Deterministic 8-category cohort comparison |
| `ReconciliationService` | `execute_run` | High (100% reusable) | Immutable run persistence, fingerprinting, and case creation |
| `IntakeService` | `verify_intake_for_snapshot` | High (100% reusable) | Regulatory approval and quota verification engine |
| `ApprovalService` | `create_configuration`, `amend_configuration`, `revoke_configuration`, `compute_seat_cap` | High (100% reusable) | Approval configuration and quota lifecycle |
| `DiscrepancyService` | `record_decision`, `get_case_detail` | High (100% reusable) | Controlled case transitions, dossiers, and append-only history |
| `ExportService` | `export_snapshot_roster`, `export_comparison_report`, `defuse_formula_injection` | High (Can be extended for PDF / Dashboard exports) | Secure formula-defused CSV/XLSX reporting |
| `StorageService` | `save_file`, `delete_file`, `get_file_path` | High (100% reusable) | File persistence and SHA-256 fingerprinting |
| `TenantGuard` | `scope_institution_id` | High (100% reusable) | Multi-tenant isolation enforcement across all APIs |

---

## 7. Concrete Backend Recommendations for Next Stages

1. **Test Suite Hygiene (Immediate Fix):**
   - Update `test_milestone_4_approval_engine.py` line 885 to use `ay = f"2024-cross-{uuid.uuid4().hex[:4]}"` so that the test suite is 100% idempotent and can be run repeatedly without collision with `uq_active_context_fingerprint`.
2. **Unified Reconciliation Integration (R2):**
   - Add a unified reconciliation orchestration method/endpoint (e.g. `POST /api/v1/reconciliation/unified-verify`) that executes both `ReconciliationService.execute_run` (cohort comparison) and `IntakeService.verify_intake_for_snapshot` (statutory intake verification) on a candidate snapshot in one coordinated workflow.
   - Extend `ComparisonService` or the reconciliation pipeline to query for concurrent active enrollments across external institutions in the same academic year (`CROSS_INSTITUTION_DUPLICATE`).
3. **Authorised Student Verification Journey (R4):**
   - Create `app/api/v1/verification.py` router and `app/services/verification_service.py`.
   - Implement:
     - `POST /api/v1/verification/requests`: Record verification request with purpose, verifier ID, student identifier, and audit log.
     - `GET /api/v1/verification/verify-student`: Minimal field disclosure endpoint returning only essential verification facts with masked APAAR.
     - `GET /api/v1/verification/certificates/{certificate_id}/qr`: Synthetic certificate identity linkage and QR verification payload.
4. **Aggregated Dashboard & Reporting Endpoints (R5):**
   - Add `GET /api/v1/dashboard/institution` and `GET /api/v1/dashboard/regulatory` providing live aggregated statistics from the database.
   - Add PDF report generation in `ExportService` for discrepancy dossiers and intake reconciliation summaries.
5. **Demonstration Dataset & Seeders (R6):**
   - Generate sample CSV demonstration files under `demo_data/` or `backend/demo_data/`.
   - Enrich `backend/app/db/seed.py` with initial approval category allocations (TFW, EWS) and an option to seed a complete end-to-end demonstration scenario.
