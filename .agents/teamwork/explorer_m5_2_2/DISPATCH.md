# Task Assignment: Explorer M5.2-2 (Unified Reconciliation Pipeline)

## Mission
Investigate the orchestration pipeline for unified reconciliation (`POST /api/v1/reconciliation/unified`), connecting longitudinal cohort reconciliation, intake matrix verification, and duplicate checks in a single coordinated execution.

## Mandatory Reading
- Original User Request: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\ORIGINAL_REQUEST.md` (R2: Unified Reconciliation)
- Project Architecture: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\PROJECT.md`
- Domain Rules: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\DOMAIN_RULES.md`
- Existing Services: `backend/app/services/comparison_service.py`, `backend/app/services/approval_service.py`, `backend/app/api/v1/reconciliation.py`

## Focus Area
1. Inspect existing `comparison_service.py` (`run_cohort_comparison`) and `approval_service.py` (`verify_intake_against_approval`).
2. Design `POST /api/v1/reconciliation/unified`:
   - Input: `{"snapshot_id": UUID, "approval_config_id": Optional[UUID]}`
   - Execution pipeline:
     a. Validate snapshot exists and user has authorization.
     b. Run longitudinal cohort comparison ($R(t) \leftrightarrow R(t+1)$).
     c. Run intake matrix compliance check if approval config exists or auto-detect active approval matrix for the institution/programme/academic year.
     d. Run cross-institution duplicate check for students in this snapshot.
     e. Aggregate findings into unified response and emit discrepancy records without duplicating finding entries.
   - Output: `{"reconciliation_run_id": UUID, "snapshot_id": UUID, "cohort_summary": {...}, "intake_summary": {...}, "duplicate_candidates": [...], "status": "COMPLETED"}`
3. Check E2E integration tests: `test_t1_r2_02_unified_reconciliation_multi_stage_execution`, `test_t1_r2_03_reconciliation_preserves_separate_findings` in `backend/tests/test_e2e_integration.py`.
4. Ensure multi-tenancy and RBAC guards: `INSTITUTION_ADMIN` can only run for own snapshots; `REGULATORY_REVIEWER` and `SYSTEM_ADMIN` can run across institutions.

## Deliverables
- `analysis.md` in your working directory.
- `handoff.md` in your working directory with Observation, Logic Chain, Caveats, Conclusion, and Verification Method.


## 2026-10-30T21:40:50Z
You are explorer_m5_2_2, a read-only exploration agent.
Your working directory is: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_m5_2_2\

Read your assignment in: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_m5_2_2\DISPATCH.md
Read ORIGINAL_REQUEST.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\PROJECT.md
Read DOMAIN_RULES.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\DOMAIN_RULES.md

Focus:
Investigate unified reconciliation pipeline `POST /api/v1/reconciliation/unified`.
Design multi-stage execution connecting longitudinal cohort comparison, intake matrix compliance, and duplicate checks without duplicate finding emission.
Check compatibility with `backend/tests/test_e2e_integration.py` tests.
Write analysis.md and handoff.md in your working directory.
When complete, notify orchestrator via send_message.
