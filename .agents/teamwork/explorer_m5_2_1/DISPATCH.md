# Task Assignment: Explorer M5.2-1 (Duplicate Detection Engine)

## Mission
Investigate the backend architecture, database queries, and service design for Cross-Institution Duplicate Detection across active rosters using `apaar_blind_index`.

## Mandatory Reading
- Original User Request: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\ORIGINAL_REQUEST.md` (R2: Unified Reconciliation)
- Project Architecture: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\PROJECT.md`
- Database Schema: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\DATABASE_SCHEMA.md`
- Existing Services: `backend/app/services/comparison_service.py`, `backend/app/services/student_service.py`, `backend/app/models/roster.py`

## Focus Area
1. Inspect how `apaar_blind_index` is stored on `students` and `annual_roster_observations`.
2. Design the query/algorithm to detect cross-institution duplicate enrollment:
   - For a given academic year (or within an authoritative snapshot context), find students who appear in active roster observations across two or more distinct institutions.
   - Return masked APAAR identifier (`XXXX-XXXX-1234`), student details, institution A (id, name, programme), and institution B (id, name, programme).
   - Ensure proper handling of legitimate transfers vs dual simultaneous enrollments.
3. Design the API endpoint `GET /api/v1/reconciliation/duplicates?academic_year={year}`:
   - Request schema, RBAC guards (accessible to `REGULATORY_REVIEWER`, `SYSTEM_ADMIN`, and scoped to own institution for `INSTITUTION_ADMIN`), and response schema.
4. Check the 4 E2E duplicate tests in `backend/tests/test_e2e_integration.py` (`test_t1_r2_01_cross_institution_duplicate_detection`, `test_t1_r2_04_cross_institution_duplicate_detection_by_blind_index`) to ensure 100% parameter and schema compatibility.

## Deliverables
- `analysis.md` in your working directory.
- `handoff.md` in your working directory with Observation, Logic Chain, Caveats, Conclusion, and Verification Method.


## 2026-10-30T21:40:44Z
You are explorer_m5_2_1, a read-only exploration agent.
Your working directory is: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_m5_2_1\

Read your assignment in: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_m5_2_1\DISPATCH.md
Read ORIGINAL_REQUEST.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\PROJECT.md
Read DATABASE_SCHEMA.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\DATABASE_SCHEMA.md

Focus:
Investigate backend cross-institution duplicate detection using `apaar_blind_index`.
Design query/algorithm, schemas, RBAC, and check compatibility with `backend/tests/test_e2e_integration.py` duplicate tests.
Write analysis.md and handoff.md in your working directory.
When complete, notify orchestrator via send_message.
