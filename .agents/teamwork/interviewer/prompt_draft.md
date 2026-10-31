Integrate Milestones 1–4 into one coherent, demonstrable APAAR-based student data management and regulatory verification platform.

Working directory: c:\Users\moham\OneDrive\Desktop\SIH26\26263
Integrity mode: development

## Reference Material
- Active Workspace: `c:\Users\moham\OneDrive\Desktop\SIH26\26263`
- Database: PostgreSQL on 127.0.0.1:5432, DB: `apaar_setu`, user: `postgres`, password: `root`
- Alembic Head: `0005_approval_intake_matrix`
- Python Virtualenv: `.\backend\venv\Scripts\python.exe`
- Existing Pytest Baseline: 135 passing tests (`pytest backend/tests/ -v`)
- Frontend Stack: React 18, TypeScript, Tailwind CSS, Vite (`npm run build`)
- Core Seeded Accounts:
  - `admin@apex.edu.in` / `Apex@12345` (Apex Institute of Technology - `INSTITUTION_ADMIN`)
  - `admin@polytechnic.edu.in` / `Poly@12345` (National Polytechnic College - `INSTITUTION_ADMIN`)
  - `reviewer@aicte.gov.in` / `Reviewer@12345` (AICTE Regulatory Officer - `REGULATORY_REVIEWER`)
  - `sysadmin@aicte.gov.in` / `Admin@12345` (System Administrator - `SYSTEM_ADMIN`)
  - `verifier@tcs.com` / `Verifier@12345` (Third Party Verifier - `THIRD_PARTY_VERIFIER`)
- Key Audit References:
  - `C:\Users\moham\.gemini\antigravity\brain\ef747daf-2171-4218-a898-ee3ea3f4ed39\milestone_4_independent_audit.md`
  - `C:\Users\moham\.gemini\antigravity\brain\milestone_4_completion_report.md`
  - `C:\Users\moham\.gemini\antigravity\brain\phase_3e_independent_audit.md`

## Verification Resources
- Regression Test Suite: `.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v` (135 passing tests baseline)
- Frontend Production Build: `npm run build`
- Architecture & Domain Specifications:
  - `API_CONTRACTS.md`
  - `DATABASE_SCHEMA.md`
  - `DOMAIN_RULES.md`
  - `PRD.md`
  - `SECURITY_MODEL.md`
  - `SYSTEM_ARCHITECTURE.md`

## Requirements

### R1. Workstream 1 — End-to-end Institutional Submission
Demonstrate the end-to-end flow: Institution → Upload → Mapping → Validation → APAAR checks → Student repository → Roster snapshot. Preserve original submissions and versioned corrections.

### R2. Workstream 2 — Unified Reconciliation
Connect APAAR identity validation, cross-institution duplicate checks, longitudinal cohort reconciliation, admission and transfer evidence, and approval configuration/intake reconciliation. Use the same student, programme, academic year, and submission context wherever applicable. Do not silently merge separate findings or duplicate-count students.

### R3. Workstream 3 — Unified Discrepancy Investigation
Demonstrate the complete lifecycle: Finding → Evidence dossier → Institutional response → Regulatory review → Decision → Audit history. Preserve the existing Phase 3E state machine, tenant isolation, and append-only decision history.

### R4. Workstream 4 — Authorised Student Verification
Implement or complete the authorised verification journey: verification request with stated purpose, authentication and role checks, consent or other valid authorisation checks applicable to prototype, minimal field disclosure, masked APAAR by default, audited request/decision/disclosure, and synthetic certificate identity linkage with QR verification demonstration. Do not claim official APAAR or AICTE integration unless a real authorised integration exists.

### R5. Workstream 5 — Regulatory Dashboards and Reports
Provide an institution-level dashboard, AICTE/regulatory overview, cohort and intake exception summaries, pending and resolved discrepancy cases, and reproducible CSV/PDF reports with source, snapshot, and rule-version references. All metrics must derive from actual backend data.

### R6. Workstream 6 — Demo Environment & Implementation Discipline
Prepare a clearly labelled synthetic dataset with multiple institutions, multiple programmes and academic years, continuing students, documented transfers, missing/ambiguous APAAR cases, unexplained cohort appearances/disappearances, intake excess, supernumerary allocations, lateral-entry cases, and missing approval evidence. Create one coherent demonstration narrative covering upload through regulatory decision.
First inspect the repository and provide:
1. Existing capability map
2. Missing end-to-end links
3. Reusable services and APIs
4. Integration architecture
5. Implementation stages
6. Acceptance tests
Preserve all existing Milestone 1–4 functionality. Do not rewrite working subsystems without demonstrated defects. Do not claim official government integration or statutory compliance based solely on synthetic data.

## Acceptance Criteria

### Quality Gates & Regression Verification
- [ ] Complete backend regression suite passes cleanly with zero failures (all 135 existing tests pass).
- [ ] Integration tests spanning multiple milestones are implemented and pass.
- [ ] Tenant-isolation and role-authorization tests pass.
- [ ] Verification privacy and disclosure tests pass (minimal disclosure, masked APAAR).
- [ ] Frontend production build succeeds (`npm run build`).
- [ ] End-to-end demonstration test runs and succeeds.
- [ ] `git diff --check` passes with no whitespace or merge conflict markers.
- [ ] Demonstration report is produced documenting actual test results, changed files, remaining gaps, and exact steps to run the demonstration.
