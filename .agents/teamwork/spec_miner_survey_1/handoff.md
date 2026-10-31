# Handoff Report: Spec Miner Survey 1 (Milestone 5 Requirements & Constraints Matrix)

**Author:** Spec Miner (`teamwork_spec_miner`)  
**Target Recipient:** Lead Architect / Parent Orchestrator (`b171c640-6691-4f51-bba8-7f9cd36c2490`)  
**Working Directory:** `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\spec_miner_survey_1\`  
**Date:** 2026-10-30T20:28:00Z  
**Handoff Type:** Hard (Task Complete)  

---

## 1. Observation

Direct code-level and specification inspection across the active workspace and audit archives yielded the following concrete observations:

1. **Original User Request & Mission Parameters:**
   - File: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\ORIGINAL_REQUEST.md`
   - Line 5: *"Integrate Milestones 1–4 into one coherent, demonstrable APAAR-based student data management and regulatory verification platform."*
   - Lines 41–57: Workstreams R1 to R6 covering End-to-end Institutional Submission (R1), Unified Reconciliation (R2), Unified Discrepancy Investigation (R3), Authorised Student Verification (R4), Regulatory Dashboards and Reports (R5), and Demo Environment & Implementation Discipline (R6).
   - Lines 70–78: Acceptance criteria requiring zero regression across existing 135 tests, integration tests, tenant isolation, masked APAAR privacy, clean frontend build (`npm run build`), and `git diff --check`.

2. **Core Architectural & Domain Rules Invariants:**
   - `PRD.md` (Lines 111–138, 655–742): Longitudinal Cohort Integrity Engine reconstructs student population transitions across consecutive academic years ($R(t) \leftrightarrow R(t+1)$), separating continuing students from arrivals and departures without automated fraud labeling.
   - `DOMAIN_RULES.md` (Lines 53–86): Snapshot completeness (`completeness_status`: `COMPLETE`, `PARTIAL`, `UNKNOWN`) is strictly decoupled from lifecycle status (`ACTIVE`, `SUPERSEDED`). Invariant: If base snapshot is `PARTIAL` or `UNKNOWN`, absent students evaluate to `UNCERTAIN_HISTORICAL_BASELINE` (`INSUFFICIENT_EVIDENCE`), never `UNEXPLAINED_DISAPPEARANCE`.
   - `DOMAIN_RULES.md` (Lines 116–147): Documented 12-digit numeric format validation ONLY (`^\d{12}$` or `^\d{4}-\d{4}-\d{4}$`). Invented checksums prohibited. Missing APAAR yields provisional identity (`MISSING_APAAR`); invalid format produces reviewable provisional record with warning. Weak attributes (matching names) never merge identities.
   - `DATABASE_SCHEMA.md` (Lines 207–210, 388–397, 507–511):
     - `uq_student_identities_apaar_blind_index` enforces uniqueness of non-null HMAC blind indexes across all institutions.
     - `uq_active_context_fingerprint` enforces retry-safe contextual deduplication on `(institution_id, programme_id, academic_year, submission_type, file_fingerprint)` where status is not `FAILED` or `CANCELLED`.
     - `idx_uq_authoritative_snapshot` guarantees at most one authoritative snapshot per `(institution, programme, academic_year)`.
   - `SECURITY_MODEL.md` (Lines 11–21, 57–72, 96–104, 126–163):
     - Argon2id password hashing ($m=64\text{ MB}, t=3, p=4$).
     - Dual cryptographic key separation: AES-256-GCM ciphertext (`encrypted_apaar_reference`) vs HMAC-SHA256 blind index (`apaar_blind_index`).
     - Opaque CSPRNG tokens (`secrets.token_urlsafe(32)`) in `verification_tokens` table for QR verification; returns masked name (`A**** V****`), programme, and status.
     - Tamper-evident linear audit ledger protected by transaction-level PostgreSQL advisory lock `pg_advisory_xact_lock(197410)`.

3. **Past Audit Findings & Live Regression Observation:**
   - `C:\Users\moham\.gemini\antigravity\brain\ef747daf-2171-4218-a898-ee3ea3f4ed39\milestone_4_independent_audit.md` (Lines 40–56, 88–98):
     - Anti-double-counting invariant: $\sum \text{Buckets} \equiv |\text{Unique Verified Students}|$.
     - Programme-level intake findings (`scope_type = 'PROGRAMME'`, `student_identity_id = NULL`) avoid scapegoating individual students for institutional intake excess.
   - `C:\Users\moham\.gemini\antigravity\brain\ef747daf-2171-4218-a898-ee3ea3f4ed39\phase_3e_independent_audit.md` (Lines 101–114, 141–150):
     - Decision row-level locking via `select(...).with_for_update()`.
     - Mandatory justification length $\ge 10$ characters.
     - Advisory lock on idempotency keys: `pg_advisory_xact_lock(hashtextextended(lock_key, 0))`.
   - **Live Pytest Execution Result:**
     - Command: `.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -q`
     - Result: 134 passed, 1 failed in 32.16s.
     - Verbatim Failure:
       `FAILED backend/tests/test_milestone_4_approval_engine.py::test_multi_tenancy_and_role_guards`
       `psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "uq_active_context_fingerprint"`
       `DETAIL: Key (institution_id, programme_id, academic_year, submission_type, file_fingerprint)=(7ffb378d-9eda-4342-a727-4fb6cbc9b18b, 6b9b9092-0d19-4ee1-94ac-30aa4fd09e24, 2024-cross-01, ANNUAL_ROSTER, 8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92) already exists.`
     - Root cause: Line 885 of `test_milestone_4_approval_engine.py` hardcoded academic year `"2024-cross-01"`. A previous test execution committed that exact tuple on the live PostgreSQL instance, causing repeat runs to violate contextual idempotency.

4. **Existing Codebase Baseline & Missing Gaps:**
   - Reusable Services: `identity_service.py`, `ingestion_service.py`, `preview_service.py`, `parser_service.py`, `snapshot_service.py`, `comparison_service.py`, `reconciliation_service.py`, `approval_service.py`, `intake_service.py`, `discrepancy_service.py`.
   - Missing Components:
     - `verification_tokens` model/migration and `/api/v1/verification` router.
     - `/api/v1/duplicate-detection` router.
     - Aggregated dashboard stats & reproducible CSV/PDF report export router (`/api/v1/reports`).
     - Multi-institution 300–500 record synthetic demonstration dataset in `backend/app/db/seed.py`.

---

## 2. Logic Chain

1. **Tracing from Objective to Subsystems:**
   The objective is to unify Milestones 1–4 into an integrated demonstration platform (Obs 1). The repository already contains complete, verified domain engines for data submission, snapshot promotion, longitudinal cohort analysis, approval intake verification, and discrepancy decisions (Obs 2, Obs 4).
   
2. **Identifying the Integration Seams:**
   Because each milestone was implemented in successive phases, the remaining work is not rebuilding core logic, but connecting existing subsystems:
   - Intake reconciliation generates `scope_type='PROGRAMME'` cases, while cohort comparison generates `scope_type='STUDENT'` cases. Both feed into `DiscrepancyCase` (Obs 2, Obs 3). The UI dossier modal must render both seamlessly.
   - Public verification and certificate QR codes require the `verification_tokens` table and `/api/v1/verification` endpoints specified in `DATABASE_SCHEMA.md` and `SECURITY_MODEL.md` (Obs 2, Obs 4).
   - Cross-institution duplicate detection requires an endpoint querying `apaar_blind_index` collisions across distinct institutions during overlapping years without transfer events (Obs 2).

3. **Analyzing the Test Isolation Failure:**
   The single test failure observed in `test_multi_tenancy_and_role_guards` directly demonstrates the strictness of the `uq_active_context_fingerprint` partial unique index (Obs 3). It proves that the database idempotency protection works exactly as specified. However, for automated test suites executing against a shared development database, test helpers must avoid hardcoded academic years and file payloads.

4. **Deriving the Milestone 5 Matrix:**
   By grounding the requirements directly in `PRD.md`, `DOMAIN_RULES.md`, `SECURITY_MODEL.md`, `API_CONTRACTS.md`, and past audit records, a complete matrix for Workstreams R1–R6 was synthesized into `spec_matrix.md`, complete with state machines, invariants, acceptance gates, and edge cases.

---

## 3. Caveats

1. **STRICTLY READ-ONLY Execution:** In accordance with Spec Miner instructions, zero production or test code was modified. The test failure in `test_multi_tenancy_and_role_guards` was documented as an observation and pitfall; resolving it by randomizing the test academic year is left to the development subagents.
2. **External Integration Disclaimer:** Verification adapters and external gateway mocks simulate regulatory validation; per PRD instructions, no claim of live statutory DigiLocker/APAAR integration is made.
3. **Database Pre-requisite:** PostgreSQL 18 on `127.0.0.1:5432` (`apaar_setu`) is assumed running with Alembic migration head `0005_approval_intake_matrix`.

---

## 4. Conclusion

1. **State of the Codebase:** The platform has solid foundational engineering with 134 passing regression tests, strict database-level concurrency protections, Argon2id security, AES-256-GCM + blind index separation, and mathematically sound intake and cohort engines.
2. **Specification Matrix Delivered:** A comprehensive, authoritative 10-section requirements document has been produced at `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\spec_miner_survey_1\spec_matrix.md`.
3. **Actionable Roadmap for Developers:**
   - Implement `verification_tokens` and `/api/v1/verification` router (R4).
   - Implement `/api/v1/duplicate-detection` router (R2).
   - Implement `/api/v1/reports` dashboard aggregation and reproducible export router (R5).
   - Unify Discrepancy Queue for both programme and student scopes (R3).
   - Enrich `db/seed.py` with multi-institution, multi-programme, 3-year synthetic data (R6).
   - Fix test isolation collision in `test_multi_tenancy_and_role_guards` (R6).

---

## 5. Verification Method

To independently verify all findings in this survey:

1. **Inspect Deliverables:**
   - View `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\spec_miner_survey_1\spec_matrix.md`.
   - View `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\spec_miner_survey_1\handoff.md`.
2. **Verify Baseline Pytest Suite:**
   Run: `.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`
   Observe the 134 passing tests and inspect the `uq_active_context_fingerprint` collision on `test_multi_tenancy_and_role_guards` (line 885).
3. **Verify Frontend Production Build:**
   Run: `npm run build`
   Confirm clean TypeScript transformation and Vite bundling.
4. **Verify Database Head:**
   Run: `cd backend && .\venv\Scripts\alembic.exe current`
   Confirm Alembic head is at `0005_approval_intake_matrix`.

---
*End of Handoff Report.*
