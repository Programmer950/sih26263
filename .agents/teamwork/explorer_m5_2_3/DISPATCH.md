# Task Assignment: Explorer M5.2-3 (Frontend Cohort Explorer & Duplicate Views)

## Mission
Investigate the frontend routing, page components, and API integration for the Cohort Explorer (`/app/cohort-explorer`) and Duplicate Detection (`/app/duplicate-detection`) interfaces in React/TypeScript.

## Mandatory Reading
- Original User Request: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\ORIGINAL_REQUEST.md` (R2: Unified Reconciliation)
- Project Architecture: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\PROJECT.md`
- Frontend Survey: `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_survey_2\survey_frontend.md`
- Frontend App Routes: `src/App.tsx`, `src/pages/`

## Focus Area
1. Inspect `src/App.tsx` routes:
   - Identify existing routes for `/app/cohort-explorer` and duplicate detection.
   - Inspect existing mock/placeholder pages or navigation links.
2. Design the Cohort Explorer component:
   - Select baseline snapshot $R(t)$ and candidate snapshot $R(t+1)$.
   - Visual cohort breakdown: Continued, Departed/Disappeared, Transferred In, Lateral Entry, New Admissions.
   - Student list with search, status filters, and masked APAAR.
3. Design the Duplicate Detection component:
   - Filter by academic year.
   - Cross-institution conflict card/table: Student (masked APAAR `XXXX-XXXX-1234`), Institution A (programme, year), Institution B (programme, year).
   - "Raise Discrepancy" action triggering the existing discrepancy finding workflow.
4. Verify TypeScript compilation (`npm run build`) requirements: proper interface definitions, error handling, loading states, and zero type errors.

## Deliverables
- `analysis.md` in your working directory.
- `handoff.md` in your working directory with Observation, Logic Chain, Caveats, Conclusion, and Verification Method.


## 2026-10-30T21:40:55Z
You are explorer_m5_2_3, a read-only exploration agent.
Your working directory is: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_m5_2_3\

Read your assignment in: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_m5_2_3\DISPATCH.md
Read ORIGINAL_REQUEST.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\ORIGINAL_REQUEST.md
Read PROJECT.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\PROJECT.md
Read survey_frontend.md: c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_survey_2\survey_frontend.md

Focus:
Investigate frontend `/app/cohort-explorer` and `/app/duplicate-detection` page components and routes.
Design UI workflow, state management, API integration, and type contracts ensuring `npm run build` succeeds without type errors.
Write analysis.md and handoff.md in your working directory.
When complete, notify orchestrator via send_message.
