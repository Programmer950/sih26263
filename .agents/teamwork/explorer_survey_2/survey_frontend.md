# Comprehensive Frontend & User Workflow Survey Report

**Workspace:** `c:\Users\moham\OneDrive\Desktop\SIH26\26263`  
**Investigator:** Explorer 2 (Frontend & User Workflow Investigator)  
**Date:** 2026-10-30  
**Target Platform:** APAAR SETU — AICTE Student Record Reconciliation Platform (SIH26263)  

---

## 1. Executive Summary

A comprehensive, code-level survey was conducted on the APAAR SETU frontend codebase, user workflows, component hierarchy, build configuration, and API client bindings.

### Core Survey Findings:
1. **Production Build Status:** **PASS** (`cmd /c npm run build` succeeds in ~2.03s with 0 errors across 1667 modules, generating `dist/assets/index-BVZUSpCX.js` [464.55 kB] and `dist/assets/index-Btrsu-Qc.css` [4.66 kB]).
2. **Architecture & Routing:** Modern React 18.3.1 with React Router DOM 7.18.5, TypeScript 5.6.3, and Vite 5.4.10. Proxies `/api` to `http://localhost:8000`. Public landing page (`/about-model`) preserves the 4-layer civic-tech theoretical framework. Authenticated portal (`/app/*`) provides an enterprise layout with tenant scope and role badge.
3. **Workstream Implementation Reality:**
   - **R1 (Submissions Flow):** **0% Frontend** — `/app/submissions` is a `PlaceholderModule`, despite a full backend API (`/submissions/upload`, `/preview`, `/confirm`, `/cancel`) ready in `backend/app/api/v1/submissions.py`.
   - **R2 (Reconciliation View):** **25% Frontend** — Intake quota verification is active in `AdmissionIntakeDashboard.tsx`. But Cohort Explorer (`/app/cohort-explorer`), Cross-Institution Duplicate Detection (`/app/duplicate-detection`), and snapshot comparison are placeholders.
   - **R3 (Discrepancy Case Management):** **95% Frontend** — Exceptionally complete in `DiscrepancyDashboard.tsx` and `DiscrepancyDossierModal.tsx` with search, filtering, privacy-masked dossiers, append-only decision audit timeline, and strict state-machine transitions.
   - **R4 (Authorised Verification UI):** **5% Frontend** — `STUDENT_VERIFIER` login works (`verifier@tcs.com`), but verification pages (`/app/verification` and `/app/certificates`) are placeholders.
   - **R5 (Regulatory Dashboards & Exports):** **40% Frontend** — `Dashboard.tsx` displays live institutions and programmes, but KPI cards contain hardcoded numbers (`240/720`, `100%`, `0`). `/app/reports` is a placeholder. Backend CSV/XLSX export endpoints exist (`/snapshots/{id}/export`), but have no UI trigger buttons.
   - **R6 (Demo Environment):** **50% Frontend** — Quick-fill login buttons for Apex Admin, AICTE Reviewer, Sysadmin, and Verifier exist in `Login.tsx`. Missing Polytechnic College button; missing in-app institution switcher; missing guided end-to-end narrative UI.
4. **CSS/Styling Discrepancy:**
   - `src/index.css` defines custom CSS variables and utility classes.
   - Core pages (`Dashboard.tsx`, `StudentRepository.tsx`, `Institutions.tsx`, `Login.tsx`) use inline `style={{ ... }}` objects.
   - `AdmissionIntakeDashboard.tsx` and `DiscrepancyDashboard.tsx` use Tailwind CSS classes (`p-8`, `max-w-7xl`, `space-y-6`, `bg-indigo-600`), **yet Tailwind CSS is NOT installed in `package.json` nor linked in `index.html`**. At runtime, Tailwind styles fail to apply unless Tailwind is added or components are styled with inline styles/custom CSS.

---

## 2. Frontend Application Structure & Build Verification

### 2.1 File Layout & Stack
```
c:\Users\moham\OneDrive\Desktop\SIH26\26263/
├── package.json             # React 18.3.1, react-router-dom 7.18.5, axios 1.21.0, lucide-react 0.460.0
├── vite.config.ts           # Port 3000, proxy /api -> http://localhost:8000
├── tsconfig.json            # Target ES2020, module ESNext, strict: true
├── index.html               # Fonts: Inter, JetBrains Mono; Title & metadata
└── src/
    ├── main.tsx             # React.StrictMode mount
    ├── App.tsx              # AppRoutes, AuthProvider, Route definitions
    ├── index.css            # Custom CSS properties & civic-tech style primitives
    ├── context/
    │   └── AuthContext.tsx  # JWT authentication, session check (/auth/me), login/logout
    ├── services/
    │   └── api.ts           # Axios instance, baseURL /api/v1, Bearer JWT interceptor, 401 redirect
    ├── types/
    │   ├── approval.ts      # Quotas, EoA configurations, intake reconciliation schemas
    │   ├── auth.ts          # User roles, user summaries, institutions, programmes
    │   ├── discrepancy.ts   # Case status, decision actions, reconciliation runs
    │   └── student.ts       # Student summaries, identity status, timeline events
    ├── components/
    │   ├── layout/
    │   │   └── EnterpriseLayout.tsx # Sidebar nav, jurisdiction header, role badge, logout
    │   ├── discrepancies/
    │   │   └── DiscrepancyDossierModal.tsx # Full interactive case investigation dossier
    │   └── [11 Landing Components] (Hero, Problem, FourLayerModel, ProofChain, etc.)
    └── pages/
        ├── PreservedShowcase.tsx        # Public theoretical landing page
        ├── Login.tsx                    # Authentication page with demo quick-fill
        ├── Dashboard.tsx                # Central/institutional regulatory dashboard
        ├── Institutions.tsx             # Registry & tenant isolation viewer
        ├── StudentRepository.tsx        # Student roster, registration modal, timeline drawer
        ├── AdmissionIntakeDashboard.tsx # Approval matrix & intake verification
        ├── DiscrepancyDashboard.tsx     # Discrepancy queue & reconciliation runs
        └── PlaceholderModule.tsx        # Generic placeholder card for upcoming modules
```

### 2.2 Production Build Verification
- Command executed: `cmd /c npm run build` (invoking `tsc && vite build`).
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
- **Finding & Recommendation:** Build succeeds with 0 errors. On Windows PowerShell, executing `npm` directly invokes `npm.ps1`, which is blocked by standard Windows execution policies; developers and CI scripts should use `npm.cmd run build` or `cmd /c npm run build`.

---

## 3. Router, State Management & Role Boundaries

### 3.1 Route Map & Page Implementation State

| Route | Component | Page Type | Status | Backend Integration |
|:---|:---|:---|:---:|:---|
| `/` | Redirect to `/about-model` | Redirect | Active | None |
| `/about-model` | `<PreservedShowcase />` | Landing | Active | Static educational content |
| `/login` | `<Login />` | Auth | Active | `POST /auth/login` |
| `/app/dashboard` | `<Dashboard />` | Main Portal | Active | `GET /institutions`, `GET /institutions/{id}/programmes` (Partially hardcoded KPIs) |
| `/app/institutions` | `<Institutions />` | Registry | Active | `GET /institutions` (with search param) |
| `/app/students` | `<StudentRepository />` | Student Master | Active | `GET /students`, `POST /students`, `GET /students/{id}/timeline` |
| `/app/submissions` | `<PlaceholderModule />` | Ingestion | **Placeholder** | **Missing UI** (Backend `/submissions/*` ready) |
| `/app/apaar-validation` | `<PlaceholderModule />` | Format Check | **Placeholder** | Backend regex/duplicate checks active in ingestion |
| `/app/admission-monitoring` | `<AdmissionIntakeDashboard />` | Approvals | Active | `GET/POST /approvals/configurations`, `POST /approvals/intake/verify` |
| `/app/duplicate-detection` | `<PlaceholderModule />` | Cross-Inst | **Placeholder** | Backend comparison & cross-institution logic exists |
| `/app/cohort-explorer` | `<PlaceholderModule />` | Longitudinal | **Placeholder** | Backend `ComparisonService` exists |
| `/app/reconciliation` | `<PlaceholderModule />` | Run Ledger | **Placeholder** | `GET /reconciliation/runs` (shown as tab in DiscrepancyDashboard) |
| `/app/discrepancies` | `<DiscrepancyDashboard />` | Findings | Active | `GET /discrepancies/cases`, `POST /cases/{id}/decisions`, `GET /reconciliation/runs` |
| `/app/reviews` | `<PlaceholderModule />` | Human Inquiries | **Placeholder** | Handled inside Discrepancy Dashboard |
| `/app/verification` | `<PlaceholderModule />` | Third-Party | **Placeholder** | Seeded permissions exist; endpoints missing |
| `/app/certificates` | `<PlaceholderModule />` | QR Linkage | **Placeholder** | Endpoints missing |
| `/app/reports` | `<PlaceholderModule />` | PDF/CSV | **Placeholder** | Backend `/snapshots/{id}/export` exists |
| `/app/rules` | `<PlaceholderModule />` | Rules Config | **Placeholder** | Versioned rules in DB |
| `/app/audit` | `<PlaceholderModule />` | Ledger | **Placeholder** | Decision audit trail shown in case dossier |

### 3.2 Role Permissions & Tenancy Scoping
The frontend recognizes 4 distinct roles (`types/auth.ts`):
1. `SYSTEM_ADMIN`: National scope, full platform access, role badge `#7C3AED` (Purple).
2. `REGULATORY_REVIEWER`: AICTE Central Authority, full inquiry & approval oversight, role badge `#0D9488` (Teal).
3. `INSTITUTION_ADMIN`: Scoped to `user.institution_id`, role badge `#2563EB` (Blue). Tenancy notice appears on Institutions and Student pages.
4. `STUDENT_VERIFIER`: Third-party verifier (TCS / employer), role badge `#D97706` (Amber).

**Key Vulnerability / Gap in Client-Side Routing:**
There are no per-route role checks in `AppRoutes`. A user logged in as `STUDENT_VERIFIER` can view navigation links for `/app/institutions` and `/app/students`. While the backend correctly returns `403 Forbidden` for unauthorized API calls, the frontend renders an empty/error table rather than a purpose-built Verifier Portal or an access-restricted boundary.

---

## 4. Workstream-by-Workstream Analysis (R1 – R6)

### R1. Institutional Submission Flow
- **Goal:** Institution → Upload → Header Mapping → Validation Preview → APAAR checks → Commit / Snapshot creation.
- **Frontend State:** Currently mapped to `<PlaceholderModule moduleNumber={4} title="Data Submissions & Ingestion" />`.
- **Backend Readiness:** Fully implemented and verified in `backend/app/api/v1/submissions.py`:
  - `POST /submissions/upload` (Multipart upload, 10MB limit, SHA-256 fingerprinting, ZIP bomb check, header extraction).
  - `POST /submissions/{submission_id}/preview` (Applies column mapping config, returns preview rows, error counts, warning rows).
  - `POST /submissions/{submission_id}/confirm` (Commits draft submission, runs ingestion pipeline, creates authoritative snapshot).
  - `POST /submissions/{submission_id}/cancel` (Aborts draft).
  - `GET /submissions` & `GET /submissions/{id}` (Paginated submission history and status).
- **Missing UI Components Needed:**
  1. `RosterUploadDropzone`: Drag-and-drop CSV/XLSX file with academic year and programme dropdowns.
  2. `ColumnMappingCard`: Matching detected CSV headers (`roll_no`, `name`, `apaar_id`, `category`, `admission_date`) with canonical fields.
  3. `ValidationPreviewTable`: Visual indicator of valid rows, duplicate rows, missing APAAR warnings, and fatal errors.
  4. `SnapshotCommitBar`: Action buttons to Cancel or "Commit Submission to Roster Ledger".
  5. `SubmissionHistoryTable`: List of historical submissions with status (`DRAFT`, `COMMITTED`, `CANCELLED`).

### R2. Unified Reconciliation View
- **Goal:** Connect APAAR format validation, cross-institution duplicate checks, cohort evolution $R(t) \leftrightarrow R(t+1)$, and statutory intake reconciliation.
- **Frontend State:**
  - **Intake Reconciliation:** Active in `AdmissionIntakeDashboard.tsx`. Evaluates snapshot candidates against AICTE EoA letter caps, displays category breakdowns (TFW, Management, Lateral Entry), and generates programme-level discrepancy cases.
  - **Cohort Reconciliation ($R(t) \leftrightarrow R(t+1)$):** `/app/cohort-explorer` is a placeholder.
  - **Cross-Institution Duplicates:** `/app/duplicate-detection` is a placeholder.
  - **Reconciliation Runs:** Tab in `DiscrepancyDashboard.tsx` fetches `GET /reconciliation/runs` and displays run fingerprints, snapshot hashes, and summary counts.
- **Backend Readiness:**
  - `ComparisonService.compare_snapshots` generates 8-tier classifications: `ADDED`, `CONTINUING`, `WITHDRAWN`, `DOCUMENTED_TRANSFER`, `UNEXPLAINED_APPEARANCE`, `UNEXPLAINED_DISAPPEARANCE`, `AMBIGUOUS_IDENTITY`, `INSUFFICIENT_EVIDENCE`.
  - `GET /snapshots/{id}/compare` and `GET /snapshots/{id}/compare/export` exist.
- **Missing UI Components Needed:**
  1. `CohortComparisonExplorer`: Visual side-by-side or Sankey-style breakdown comparing Baseline Snapshot $R(t)$ vs. Candidate Snapshot $R(t+1)$.
  2. `DuplicateDetectionTable`: Filtered view of concurrent enrollments across distinct institutions sharing blind-indexed APAAR hashes.
  3. `ReconciliationTriggerModal`: Regulatory reviewer tool to execute comparisons and generate cryptographic result fingerprints.

### R3. Discrepancy Case Management
- **Goal:** Finding → Evidence dossier → Institutional response → Regulatory review → Decision → Audit history.
- **Frontend State:** **Fully Implemented and Robust.**
  - `DiscrepancyDashboard.tsx` provides:
    - Metric cards for Active Cases, High Priority, Under Review, Resolved.
    - Full-text search and filters for Status, Priority, Classification.
    - Reconciliation runs ledger toggle.
  - `DiscrepancyDossierModal.tsx` provides:
    - Neutral classification rationale (guaranteeing no presumption of non-compliance).
    - Privacy-preserving student masking (`Lock` icon, masked APAAR, internal UUID).
    - Reversible append-only decision audit trail with author attribution and prior $\rightarrow$ new status.
    - Role-aware administrative action selector:
      - `REGULATORY_REVIEWER`: `START_INVESTIGATION`, `REQUEST_EVIDENCE`, `RECORD_CORRECTION`, `CONFIRM_VALID`, `CLOSE_CASE`, `REOPEN_CASE`.
      - `INSTITUTION_ADMIN`: `SUBMIT_EXPLANATION`.
    - Mandatory minimum 10-character justification with live character counter.
    - Supporting evidence reference field.
- **Minor Enhancements Needed:**
  - Add link from Case Dossier to the Student Timeline in Student Repository.
  - Redirect the sidebar's `/app/reviews` link directly to this active discrepancy workflow.

### R4. Authorised Student Verification UI
- **Goal:** Permitted stakeholder portal: stated purpose, consent check, minimal disclosure, masked APAAR, certificate QR verification demonstration.
- **Frontend State:** `/app/verification` and `/app/certificates` are placeholders.
- **Backend State:** Role `STUDENT_VERIFIER` exists in database and seeds with permissions `{"verify_student_record": True, "verify_certificate": True}`. No dedicated API endpoints currently exist for verification tokens or certificate QR checking.
- **Missing UI Components Needed:**
  1. `VerifierDashboard`: Dedicated home view for `STUDENT_VERIFIER` role upon login.
  2. `VerificationRequestForm`: Search by Student Roll Number / APAAR ID + Institution, with mandatory Purpose dropdown (Employment Verification, Higher Studies, Loan Processing) and Consent Affirmation checkbox.
  3. `MinimalDisclosureCard`: Clean, privacy-preserving credential card presenting only: Student Name, Institution, Programme, Degree Completion / Enrolment Status, Masked APAAR, and Verification Timestamp. Demographics (DOB, category, address) are explicitly omitted.
  4. `CertificateQRViewer`: Display of synthetic institutional degree certificate with embedded authenticable QR code, alongside an interactive "Verify QR Payload" validator.

### R5. Regulatory Dashboards & Report Exports
- **Goal:** Institution-level dashboard, AICTE overview, cohort/intake exception summaries, reproducible CSV/PDF report downloads.
- **Frontend State:**
  - `Dashboard.tsx` shows monitored institutions or approved programmes.
  - Hardcoded values in `Dashboard.tsx`: Approved Intake (`240` or `720`), Cohort Reconciliation (`100%`), Pending Inquiries (`0`).
  - `/app/reports` is a placeholder.
  - No export buttons exist in the UI.
- **Backend Readiness:**
  - `ExportService` (`backend/app/services/export_service.py`) provides CSV and XLSX streaming with complete CSV Formula Injection defusing (CWE-1236):
    - `GET /snapshots/{id}/export?format=csv|xlsx`
    - `GET /snapshots/{id}/compare/export?format=csv|xlsx`
- **Missing UI Components Needed:**
  1. Dynamic metric binding on `Dashboard.tsx` (summing real approved seats, active cases, and reconciliation completion).
  2. Direct "Download Roster CSV/Excel" buttons on Snapshot lists and comparison screens.
  3. `ReportsAnalyticsPage` on `/app/reports` with reproducible report generation, source snapshot reference, and cryptographic run hashes.

### R6. Demo Environment & Demonstration Discipline
- **Goal:** Multi-institution switching, demonstration narratives, synthetic datasets with all edge cases.
- **Frontend State:**
  - `Login.tsx` has 4 quick-fill seeded accounts:
    - `admin@apex.edu.in` / `Apex@12345` (Apex Institute of Technology - `INSTITUTION_ADMIN`)
    - `reviewer@aicte.gov.in` / `Reviewer@12345` (AICTE Regulatory Officer - `REGULATORY_REVIEWER`)
    - `sysadmin@aicte.gov.in` / `Admin@12345` (System Administrator - `SYSTEM_ADMIN`)
    - `verifier@tcs.com` / `Verifier@12345` (TCS Verifier - `STUDENT_VERIFIER`)
  - Missing in Login UI: National Polytechnic College (`admin@polytechnic.edu.in` / `Poly@12345`) and Kaveri Institute (`admin@kaveri.edu.in` / `Kaveri@12345`).
  - In `EnterpriseLayout.tsx`, header displays jurisdiction (`user.institution_name || 'AICTE Central Authority'`).
  - No in-app tenant switching (requires logging out and back in).
- **Missing UI Components Needed:**
  1. Add National Polytechnic College and Kaveri Institute quick-fill buttons to `Login.tsx`.
  2. For `SYSTEM_ADMIN` and `REGULATORY_REVIEWER`, provide an in-app "Simulate Institution View" dropdown in the header.
  3. Interactive "Demonstration Walkthrough" banner linking R1 (Upload) $\rightarrow$ R2 (Reconciliation) $\rightarrow$ R3 (Discrepancy) $\rightarrow$ R4 (Verification) $\rightarrow$ R5 (Export).

---

## 5. CSS Styling Audit & Discrepancy Findings

### 5.1 The Tailwind CSS Missing Configuration Issue
- In `AdmissionIntakeDashboard.tsx` and `DiscrepancyDashboard.tsx`, elements use Tailwind utility classes:
  ```tsx
  <div className="p-8 max-w-7xl mx-auto space-y-6">
  <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
  ```
- **Problem:**
  - Neither `tailwindcss` nor `@tailwindcss/vite` / `postcss` is present in `package.json`.
  - There is no `tailwind.config.js` or `postcss.config.js`.
  - `index.html` does not load Tailwind from CDN.
  - `index.css` does not include `@tailwind` directives.
- **Impact:**
  - The build succeeds because Vite does not error on unreferenced class names.
  - However, at runtime, elements styled with pure Tailwind classes render with default browser styling or unaligned layouts unless standard inline styles or `index.css` utility classes are applied.
- **Recommended Solution:**
  - Either add Tailwind CSS to the frontend dependencies (`npm install -D tailwindcss postcss autoprefixer` or include Tailwind CDN in `index.html` for Hackathon demonstration speed), OR ensure all UI components have robust fallback inline styles and `index.css` class coverage consistent with `Dashboard.tsx` and `StudentRepository.tsx`.

---

## 6. Concrete Frontend Action Plan for Implementation Phase

| Workstream | Priority | Key Implementation Tasks | Target Files |
|:---|:---:|:---|:---|
| **R1: Submissions UI** | **P0** | Build file upload, column mapping, and preview/commit components. Replace `PlaceholderModule` on `/app/submissions`. | `src/pages/DataSubmissions.tsx`, `src/App.tsx` |
| **R2: Reconciliation UI** | **P0** | Build Longitudinal Cohort Explorer $R(t) \leftrightarrow R(t+1)$ comparing snapshot observations. Replace placeholder on `/app/cohort-explorer`. | `src/pages/CohortExplorer.tsx`, `src/App.tsx` |
| **R3: Discrepancies** | **P1** | Add direct link from case dossier to Student Repository timeline. Route `/app/reviews` to Discrepancy view. | `src/components/discrepancies/DiscrepancyDossierModal.tsx`, `src/App.tsx` |
| **R4: Student Verification** | **P0** | Implement Third-Party Verifier Portal UI with purpose limitation, consent confirmation, and masked APAAR. Build Certificate QR linkage viewer. | `src/pages/VerificationPortal.tsx`, `src/pages/CertificateLinkage.tsx` |
| **R5: Dashboards & Reports** | **P1** | Replace hardcoded dashboard KPI numbers with live aggregated metrics. Add CSV/XLSX download action buttons calling backend `/snapshots/{id}/export`. | `src/pages/Dashboard.tsx`, `src/pages/ReportsAnalytics.tsx` |
| **R6: Demo Integration** | **P1** | Add Polytechnic and Kaveri demo buttons to `Login.tsx`. Add in-app institution switcher for reviewers. | `src/pages/Login.tsx`, `src/components/layout/EnterpriseLayout.tsx` |
| **Styling Fix** | **P0** | Ensure Tailwind CSS styles render properly (via CDN or npm packages) so `AdmissionIntakeDashboard` and `DiscrepancyDashboard` render with full visual polish. | `index.html`, `package.json` |

---

## 7. Conclusion

The APAAR SETU frontend has an exceptionally strong, clean TypeScript and React 18 foundation, with zero build errors. The authentication system, student repository with timeline drawer, and Phase 3E discrepancy dossier are high-fidelity, production-grade implementations.

The primary task for Milestone integration is replacing the 4 key `PlaceholderModule` routes (Submissions, Cohort Explorer, Verifier Portal, Reports) with active functional views wired directly to the already-complete, passing backend services.
