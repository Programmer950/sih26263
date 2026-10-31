# Project: APAAR SETU Milestone 5 Integration

## Architecture
- **Framework**: FastAPI (Backend) + React 18 / TypeScript / Vite (Frontend)
- **Database**: PostgreSQL 18 (`apaar_setu`) at Alembic head `0005_approval_intake_matrix`
- **Security & Cryptography**:
  - Argon2id passwords
  - AES-256-GCM field encryption for APAAR IDs
  - HMAC-SHA256 blind indexing for cross-institution identity search without decryption
  - Chained immutable audit ledger with PostgreSQL advisory lock `pg_advisory_xact_lock(197410)`
  - Minimal field disclosure whitelist & masked APAAR (`XXXX-XXXX-1234`) for third-party verifiers
- **Module Boundaries**:
  - `backend/app/api/v1/`: REST API routers
  - `backend/app/models/`: Declarative SQLAlchemy models
  - `backend/app/services/`: Core business logic engines
  - `src/pages/`, `src/components/`: Frontend React applications
  - `data/demo_rosters/`: Synthetic CSV demo files for end-to-end demonstrations

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Baseline Test Isolation | Parametrize line 885 in `test_milestone_4_approval_engine.py` to restore 135/135 tests | M5.1 | Survey |
| 2 | Tailwind CSS Integration | Ensure Tailwind utility classes in dashboards render with full styling | M5.1 | Survey |
| 3 | E2E Test Suite Harness | Requirement-driven integration test harness spanning all workstreams | M5.1 | ORIGINAL_REQUEST |
| 4 | Cross-Institution Duplicate Detection | Query blind indexes across distinct institutions in concurrent academic years | M5.2 | R2 |
| 5 | Unified Reconciliation Pipeline | Joint execution and response for cohort comparison + statutory intake quota verification | M5.2 | R2 |
| 6 | Frontend Cohort Explorer & Duplicate UI | Interactive $R(t) \leftrightarrow R(t+1)$ transition viewer and duplicate alert board | M5.2 | R2 |
| 7 | Verification Tokens & Purpose Ledger | Opaque CSPRNG tokens, stated purpose logging, and audit trail in verification engine | M5.3 | R4 |
| 8 | Minimal Field Disclosure Whitelist | Privacy-safe student verification endpoint returning masked APAAR and basic info | M5.3 | R4 |
| 9 | Certificate Linkage & Authenticable QR | Synthetic QR verification payload with tamper-evident signature verification | M5.3 | R4 |
| 10 | Frontend Verification Portal | Verifier login journey, consent check, masked record view, and QR scanner/display | M5.3 | R4 |
| 11 | Frontend Submissions Workflow | Upload -> Column Mapping -> Validation Preview -> Atomic Confirm into Snapshot | M5.4 | R1 |
| 12 | Backend Dashboard Aggregations | Dynamic `/api/v1/dashboard/summary` metrics for institutional and regulatory overviews | M5.4 | R5 |
| 13 | Reproducible PDF & CSV Reports | Export engine embedding snapshot hashes, rule versions, and audit timestamps | M5.4 | R5 |
| 14 | Frontend Reports & Dashboard Wiring | Replace hardcoded KPIs with live data; trigger CSV/PDF downloads | M5.4 | R5 |
| 15 | Multi-Institution Synthetic Seed Data | 3 institutions, 3 programmes, 3 years, 300–500 students with documented edge cases | M5.5 | R6 |
| 16 | Demonstration Sample CSV Files | Pre-packaged roster CSVs for 2023-24 baseline, 2024-25 candidate, and corrections | M5.5 | R6 |
| 17 | Final E2E Demonstration & Regression Gate | Full regression pass (>=135 tests), frontend build, and demonstration walkthrough | M5.5 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M5.1 | Baseline Stabilization & Test Infra | Fix test isolation collision; setup E2E test harness; styling fix | none | DONE |
| M5.2 | Unified Reconciliation & Duplicate Engine | Cross-institution duplicate detection; unified reconciliation endpoint; Cohort UI | M5.1 | PLANNED |
| M5.3 | Authorised Verification & Privacy Portal | Verification tokens; purpose ledger; minimal disclosure; QR certs; Verifier UI | M5.1 | PLANNED |
| M5.4 | Submissions UI & Regulatory Reporting | Submissions frontend wizard; dashboard aggregate APIs; PDF export; Reports UI | M5.2, M5.3 | PLANNED |
| M5.5 | Synthetic Dataset, Seeders & E2E Validation | Rich multi-institution seed; demo CSV files; E2E regression verification; demo report | M5.4 | PLANNED |

## Interface Contracts

### M5.2: Unified Reconciliation ↔ UI
- **Endpoint**: `POST /api/v1/reconciliation/unified`
  - Input: `{"snapshot_id": UUID, "approval_config_id": UUID (optional)}`
  - Output: `{"reconciliation_run_id": UUID, "cohort_summary": {...}, "intake_summary": {...}, "duplicate_candidates": [...]}`
- **Endpoint**: `GET /api/v1/reconciliation/duplicates`
  - Input: `?academic_year=2024-2025`
  - Output: `List[DuplicateCandidateResponse]` (masked APAAR, institution A, institution B, programme details)

### M5.3: Verification Engine ↔ Verifier UI
- **Endpoint**: `POST /api/v1/verification/request`
  - Headers: `Authorization: Bearer <jwt_student_verifier>`
  - Input: `{"apaar_id": str, "stated_purpose": str, "consent_confirmed": bool}`
  - Output: `{"verification_id": UUID, "status": "VERIFIED" | "NOT_FOUND", "disclosed_record": {"masked_apaar": "XXXX-XXXX-1234", "masked_name": "A**** K****", "programme_name": str, "institution_name": str, "academic_year": str, "enrolment_status": str}, "token": str, "qr_payload": str}`
- **Endpoint**: `GET /api/v1/verification/qr/{token}`
  - Output: `{"valid": bool, "issued_at": str, "record": {...}}`

### M5.4: Dashboard Aggregations ↔ Dashboard UI
- **Endpoint**: `GET /api/v1/dashboard/summary`
  - Headers: `Authorization: Bearer <jwt>`
  - Output: Role-scoped counts:
    - For `INSTITUTION_ADMIN`: own enrolled students, approved intake, utilization %, open discrepancies, pending submissions.
    - For `REGULATORY_REVIEWER` / `SYSTEM_ADMIN`: total institutions, total students across institutions, intake compliance %, total open discrepancy cases.

## Code Layout
- Backend routes: `backend/app/api/v1/`
  - `verification.py` (New: Workstream 4)
  - `dashboard.py` (New: Workstream 5)
  - `reconciliation.py` (Updated: Workstream 2)
- Backend services: `backend/app/services/`
  - `verification_service.py` (New: Workstream 4)
  - `export_service.py` (Updated: PDF report generation)
  - `comparison_service.py` (Updated: cross-institution duplicate check)
  - `dashboard_service.py` (New: aggregated statistics)
- Backend tests: `backend/tests/`
  - `test_e2e_integration.py` (New: E2E Integration Test Suite)
- Frontend: `src/`
  - `pages/Submissions.tsx` (New: Workstream 1)
  - `pages/CohortExplorer.tsx` (New: Workstream 2)
  - `pages/VerificationPortal.tsx` (New: Workstream 4)
  - `pages/Reports.tsx` (New: Workstream 5)
- Demo data: `data/demo_rosters/`
  - `apex_roster_2023_24.csv`
  - `apex_roster_2024_25_candidate.csv`
  - `polytechnic_roster_2024_25.csv`
