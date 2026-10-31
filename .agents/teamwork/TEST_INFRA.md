# E2E Test Infra: APAAR SETU Milestone 5 Integration

## Test Philosophy
- Opaque-box, requirement-driven derived directly from `ORIGINAL_REQUEST.md` and domain specifications.
- Complete regression preservation: existing 135 tests must pass 100%.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Workload Testing.

## Feature Inventory & Test Mapping
| # | Feature | Workstream | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) | Tier 4 (Scenario) |
|---|---------|------------|:-----------------:|:-----------------:|:----------------------:|:-----------------:|
| 1 | Institutional Submission Pipeline | R1 | 5 tests | 5 tests | ✓ | Scenario 1 |
| 2 | Unified Reconciliation & Duplicate Detection | R2 | 5 tests | 5 tests | ✓ | Scenario 2 |
| 3 | Discrepancy Lifecycle & Append-Only Decisions | R3 | 5 tests | 5 tests | ✓ | Scenario 3 |
| 4 | Authorised Student Verification (Masked APAAR, QR) | R4 | 5 tests | 5 tests | ✓ | Scenario 4 |
| 5 | Regulatory Dashboards & Reproducible Export | R5 | 5 tests | 5 tests | ✓ | Scenario 5 |
| 6 | Synthetic Multi-Institution Demonstration Flow | R6 | 5 tests | 5 tests | ✓ | E2E Walkthrough |

## Test Architecture
- **Location**: `backend/tests/test_e2e_integration.py`
- **Execution Command**: `.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_e2e_integration.py -v`
- **Full Regression Command**: `.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`
- **Frontend Build Command**: `cmd /c npm run build`
- **Pass Semantics**: Zero failures, zero warnings treated as errors, clean exit code 0.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| 1 | Institutional Upload to Authoritative Snapshot | Upload CSV, preview mapping, confirm, verify snapshot promotion | Snapshot active, students in repository |
| 2 | Longitudinal Cohort & Intake Reconciliation | Run unified reconciliation on consecutive years | Discrepancies raised for intake excess & cohort changes |
| 3 | Discrepancy Dossier & Regulatory Decision | Institution responds to case, AICTE reviewer decides | Append-only decision recorded, case resolved |
| 4 | External Verifier Purpose-Stated Request | Third-party login, request record by APAAR, check minimal disclosure | Masked APAAR returned, audit logged, QR verifiable |
| 5 | Regulatory Dashboard & PDF/CSV Export | Fetch dashboard summary, export snapshot report | Real metrics returned, report generated with fingerprint |

## Coverage Thresholds
- Tier 1: ≥5 per workstream (≥30 tests)
- Tier 2: ≥5 boundary cases per workstream (≥30 tests)
- Tier 3: Pairwise combinations across workstreams
- Tier 4: ≥5 realistic end-to-end user journeys
- Zero regression on existing 135 tests.
