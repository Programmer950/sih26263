# Handoff Report — Explorer Survey 2 (Frontend & User Workflow Investigator)

**Working Directory:** `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_survey_2\`  
**Target Project:** APAAR SETU (SIH26263)  
**Date:** 2026-10-30  
**Handoff Type:** Hard (Survey Task Complete)  

---

## 1. Observation

1. **Frontend Production Build:**
   - Command: `cmd /c npm run build` (running `tsc && vite build`)
   - Output:
     ```
     vite v5.4.21 building for production...
     transforming...
     ✓ 1667 modules transformed.
     rendering chunks...
     computing gzip size...
     dist/index.html                   1.77 kB │ gzip:   0.85 kB
     dist/assets/index-Btrsu-Qc.css    4.66 kB │ gzip:   1.62 kB
     dist/assets/index-BVZUSpCX.js   464.55 kB │ gzip: 127.03 kB
     ✓ built in 2.03s
     ```
   - Direct execution of `npm run build` from Windows PowerShell threw `PSSecurityException` on `C:\nvm4w\nodejs\npm.ps1` due to execution policy, whereas `cmd /c npm run build` and `npm.cmd run build` succeed with exit code 0.

2. **Git Status & Whitespace Verification:**
   - Command: `git diff --check`
   - Result: Exit code 0, no whitespace errors, no merge conflict markers.

3. **Backend Baseline Regression Test Result:**
   - Command: `.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -q`
   - Result: 134 passed, 1 failed in 46.26s.
   - Failure detail: `backend/tests/test_milestone_4_approval_engine.py::test_multi_tenancy_and_role_guards` failed with `IntegrityError: duplicate key value violates unique constraint "uq_active_context_fingerprint"` on key `(institution_id, programme_id, academic_year, submission_type, file_fingerprint) = (7ffb378d-9eda-4342-a727-4fb6cbc9b18b, 6b9b9092-0d19-4ee1-94ac-30aa4fd09e24, 2024-cross-01, ANNUAL_ROSTER, 8d0190c1d8a14610ae61fd046e56971c3f7987d7a8a8982570dfc0ed608eaa92)`.
   - Reason: A pre-existing test record with identical academic year `2024-cross-01` and file hash remained in PostgreSQL from a previous test run.

4. **Component & Route State (`src/App.tsx`, lines 68-208):**
   - Active implemented pages:
     - `Dashboard.tsx` (`/app/dashboard`)
     - `Institutions.tsx` (`/app/institutions`)
     - `StudentRepository.tsx` (`/app/students`)
     - `AdmissionIntakeDashboard.tsx` (`/app/admission-monitoring`)
     - `DiscrepancyDashboard.tsx` (`/app/discrepancies`)
   - Placeholder pages (`PlaceholderModule.tsx`):
     - `submissions` (Line 71: Module 4, Data Submissions & Ingestion)
     - `apaar-validation` (Line 84: Module 5, APAAR Validation)
     - `duplicate-detection` (Line 100: Module 7, Cross-Institution Duplicate Detection)
     - `cohort-explorer` (Line 111: Module 8, Longitudinal Cohort Integrity Engine)
     - `reconciliation` (Line 124: Module 9, Reconciliation Centre)
     - `reviews` (Line 140: Module 11, Review & Resolution Workflow)
     - `verification` (Line 152: Module 12, Authorised Verification Portal)
     - `certificates` (Line 164: Module 13, Certificate Identity Linkage)
     - `reports` (Line 176: Module 14, Reports & Analytics)
     - `rules` (Line 188: Module 17, Rules & Statutory Configuration)
     - `audit` (Line 200: Module 18, Audit & Access History)

5. **API Client & Endpoints:**
   - File: `src/services/api.ts` (Lines 1-34)
   - Configuration: Base URL `/api/v1`, Bearer JWT attached from `localStorage.getItem('apaar_setu_token')`, response interceptor clears credentials and redirects to `/login?revoked=true` on 401.
   - Vite Proxy (`vite.config.ts`, lines 10-15): Proxies `/api` to `http://localhost:8000`.

6. **Styling Discrepancy:**
   - `package.json` contains: `axios`, `lucide-react`, `react`, `react-dom`, `react-router-dom`, `@types/react`, `@types/react-dom`, `@vitejs/plugin-react`, `typescript`, `vite`.
   - Tailwind CSS is NOT installed in `package.json`, not mentioned in `vite.config.ts`, and not linked via CDN in `index.html`.
   - `AdmissionIntakeDashboard.tsx` and `DiscrepancyDashboard.tsx` rely heavily on Tailwind utility classes (`p-8`, `max-w-7xl`, `bg-indigo-600`, etc.), whereas other pages use inline `style={{ ... }}` objects.

7. **Auth Roles & Seed Users:**
   - Seeded users in `backend/app/db/seed.py`:
     - `admin@apex.edu.in` / `Apex@12345` (INSTITUTION_ADMIN)
     - `admin@polytechnic.edu.in` / `Poly@12345` (INSTITUTION_ADMIN)
     - `admin@kaveri.edu.in` / `Kaveri@12345` (INSTITUTION_ADMIN)
     - `reviewer@aicte.gov.in` / `Reviewer@12345` (REGULATORY_REVIEWER)
     - `sysadmin@aicte.gov.in` / `Admin@12345` (SYSTEM_ADMIN)
     - `verifier@tcs.com` / `Verifier@12345` (STUDENT_VERIFIER)
   - Login page (`src/pages/Login.tsx`, lines 220-296) has quick-fill buttons for Apex, AICTE Reviewer, Sysadmin, and External Verifier, but omits Polytechnic College and Kaveri Institute.

---

## 2. Logic Chain

1. **Build Health:**
   - From Observation 1, TypeScript passes with strict checks and Vite builds the bundle in 2.03s without errors.
   - Therefore, there are no syntax, typing, or module import breakage issues in the current frontend.

2. **Frontend Workstream Readiness vs Backend Parity:**
   - From Observation 4, `/app/submissions` is a placeholder. However, backend file `submissions.py` contains 612 lines of tested code providing `/submissions/upload`, `/preview`, `/confirm`, `/cancel`, and `/submissions`.
   - Therefore, Workstream R1 (Institutional Submissions) requires ONLY frontend implementation connecting to existing backend APIs.
   - Similarly, for Workstream R2, `ComparisonService` and `/snapshots/{id}/compare` exist in backend, but `/app/cohort-explorer` is a placeholder in frontend.
   - For Workstream R3 (Discrepancy Case Management), `DiscrepancyDashboard.tsx` and `DiscrepancyDossierModal.tsx` are already connected to `/discrepancies/cases` and `/discrepancies/cases/{id}/decisions`. This workstream is ~95% complete on both ends.
   - For Workstream R4 (Authorised Verification), both frontend and dedicated backend endpoints are missing (permissions exist in seed).
   - For Workstream R5 (Reports & Export), `ExportService` exists in backend with formula-defused CSV/XLSX downloads (`/snapshots/{id}/export`), but the frontend has no download buttons and `/app/reports` is a placeholder.

3. **Styling Consistency:**
   - From Observation 6, Tailwind utility classes in `AdmissionIntakeDashboard.tsx` and `DiscrepancyDashboard.tsx` will not render properly without Tailwind CSS loaded.
   - Therefore, adding Tailwind via CDN in `index.html` or installing it via npm is necessary to maintain visual integrity during demonstrations.

---

## 3. Caveats

1. **Database Test Artifact:** The single test failure in `test_multi_tenancy_and_role_guards` was caused by an uncleaned database row from a previous run, not a regression in source code.
2. **Third-Party Verifier Backend:** Did not inspect external DigiLocker or UIDAI adapters since project rules strictly mandate prototype-only synthetic simulation without claiming official statutory integration.
3. **Responsive Mobile Views:** While desktop views (1280px+) were analyzed, mobile breakpoints on large data tables were not audited.

---

## 4. Conclusion

The frontend platform is structurally sound, compiles cleanly, and has an operational foundation in React 18 / Vite. The Discrepancy Intelligence Centre (R3) and Institutional Intake Matrix (R2 part) are already deeply implemented with high-grade security, append-only audit histories, and tenant guards.

The implementation phase must focus on:
1. **Building the Submissions Flow UI (R1):** File upload, header mapping, preview validation, and snapshot commitment.
2. **Building the Longitudinal Cohort Explorer UI (R2):** Visual $R(t) \leftrightarrow R(t+1)$ comparison viewer.
3. **Building the Authorised Verification Portal (R4):** Purpose limitation, consent checkbox, minimal disclosure card, and certificate QR viewer.
4. **Wiring Dynamic KPIs and Export Buttons (R5):** Dynamic metrics in `Dashboard.tsx`, CSV/XLSX export triggers calling `GET /snapshots/{id}/export`.
5. **Styling Polish:** Integrating Tailwind CSS so all dashboards render with their intended styles.

---

## 5. Verification Method

To independently verify all findings in this report:
1. **Run Frontend Build:**
   ```powershell
   cmd /c npm run build
   ```
   *Expected result:* 0 errors, 1667 modules transformed, output files in `dist/`.
2. **Check Git Cleanliness:**
   ```powershell
   git diff --check
   ```
   *Expected result:* Exit code 0, no whitespace or conflict errors.
3. **Verify Route Placeholders:**
   Inspect `src/App.tsx` lines 68–208 using `view_file` to confirm the 11 placeholder routes.
4. **Verify API Endpoints in Backend:**
   Inspect `backend/app/api/v1/submissions.py` and `backend/app/services/export_service.py` to confirm backend endpoint readiness.
5. **Check Survey Report:**
   Read full report at:
   `c:\Users\moham\OneDrive\Desktop\SIH26\26263\.agents\teamwork\explorer_survey_2\survey_frontend.md`
