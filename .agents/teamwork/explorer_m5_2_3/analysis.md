# Comprehensive Analysis & Engineering Design: Frontend Cohort Explorer & Cross-Institution Duplicate Detection

**Agent ID:** `explorer_m5_2_3`  
**Milestone:** M5.2 (Unified Reconciliation & Duplicate Views)  
**Workspace:** `c:\Users\moham\OneDrive\Desktop\SIH26\26263`  
**Date:** 2026-10-30  
**Target Routes:** `/app/cohort-explorer`, `/app/duplicate-detection`  
**Target Stack:** React 18.3.1, TypeScript 5.6.3, Vite 5.4.10, Tailwind CSS (via `index.html`), Axios 1.21.0, Lucide React 0.460.0  

---

## 1. Executive Summary

This document specifies the complete architectural design, component hierarchy, state management, API integration, and type contracts for replacing the two placeholder modules in the APAAR SETU platform:
1. **Longitudinal Cohort Integrity Engine** (`/app/cohort-explorer`): The flagship signature innovation of APAAR SETU that reconstructs year-over-year cohort evolution ($R(t) \leftrightarrow R(t+1)$), isolating unexplained appearances and departures under identical headcounts, and breaking down cohorts into **Continued, Departed/Disappeared, Transferred In, Lateral Entry, and New Admissions**.
2. **Cross-Institution Duplicate Detection** (`/app/duplicate-detection`): A regulatory board detecting simultaneous concurrent enrollments across distinct institutions sharing blind-indexed APAAR references (`HMAC-SHA256`) without decrypting sensitive identities, with an interactive dual-institution comparative card/table and an actionable **"Raise Discrepancy"** workflow integrated directly into the Phase 3E discrepancy dossier state machine.

Both components are designed to strictly guarantee:
- **Zero TypeScript errors** (`tsc --noEmit` and `npm run build` PASS).
- **Strict multi-tenancy & role awareness** (`INSTITUTION_ADMIN` locked to own campus; `REGULATORY_REVIEWER` and `SYSTEM_ADMIN` granted multi-institution oversight).
- **Consistent UI/UX design language** matching `AdmissionIntakeDashboard.tsx` and `DiscrepancyDashboard.tsx`.
- **Complete asynchronous fault tolerance** with loading skeletons, retry triggers, and explainable non-punitive audit banners.

---

## 2. Existing Codebase Audit & Route Integration

### 2.1 Current Route Configuration (`src/App.tsx`)
In `src/App.tsx`, both routes currently render `PlaceholderModule`:
```tsx
// Line 97 in src/App.tsx
<Route
  path="duplicate-detection"
  element={
    <PlaceholderModule
      moduleNumber={7}
      title="Cross-Institution Duplicate Detection"
      milestone="Milestone 5"
      description="Detects concurrent active enrollments across institutions using blind-indexed APAAR references without decrypting the full database."
      keyEntities={['student_identities', 'transfer_events', 'reconciliation_findings']}
    />
  }
/>

// Line 109 in src/App.tsx
<Route
  path="cohort-explorer"
  element={
    <PlaceholderModule
      moduleNumber={8}
      title="Longitudinal Cohort Integrity Engine"
      milestone="Milestone 6"
      signature={true}
      description="Signature innovation: Reconstructs year-over-year cohort evolution (R(t) ↔ R(t+1)), isolating unexplained appearances and departures under identical headcount."
      keyEntities={['roster_snapshots', 'annual_roster_observations', 'reconciliation_runs', 'reconciliation_findings']}
    />
  }
/>
```

### 2.2 Sidebar Navigation (`src/components/layout/EnterpriseLayout.tsx`)
In `src/components/layout/EnterpriseLayout.tsx` (lines 45–46), sidebar navigation links already exist and point directly to these routes:
```tsx
{ name: 'Cross-Institution Checks', path: '/app/duplicate-detection', icon: GitCompare },
{ name: 'Cohort Explorer', path: '/app/cohort-explorer', icon: Layers, badge: 'Signature' },
```
No navigation path changes are required. Replacing the elements in `src/App.tsx` activates the full end-to-end user journey immediately.

### 2.3 Styling Foundation
`index.html` loads Tailwind CSS via CDN (`https://cdn.tailwindcss.com`) with Inter and JetBrains Mono fonts. The new components use standard Tailwind utility classes (`bg-slate-50`, `border-slate-200`, `rounded-xl`, `shadow-sm`, `text-indigo-600`, etc.) paired with inline fallback styling consistent with the existing codebase (`StudentRepository.tsx`, `AdmissionIntakeDashboard.tsx`, `DiscrepancyDashboard.tsx`).

---

## 3. Type Contract Specifications

To prevent type ambiguity and ensure clean modularization, we define two dedicated TypeScript type definitions:
1. `src/types/cohort.ts`
2. `src/types/duplicate.ts`

### 3.1 Cohort Explorer Contracts (`src/types/cohort.ts`)
```typescript
import { DiscrepancyClassification, ReviewPriority } from './discrepancy';

export type CohortDisplayCategory =
  | 'ALL'
  | 'CONTINUING'
  | 'NEW_ADMISSIONS'
  | 'LATERAL_ENTRY'
  | 'TRANSFERRED_IN'
  | 'DEPARTED'
  | 'UNEXPLAINED_APPEARANCE'
  | 'UNEXPLAINED_DISAPPEARANCE'
  | 'AMBIGUOUS_IDENTITY';

export interface ComparisonRecordItem {
  student_identity_id: string;
  internal_student_uuid: string;
  student_name: string;
  masked_apaar?: string | null;
  classification: DiscrepancyClassification;
  explanation: string;
  source_status_baseline?: string | null;
  source_status_candidate?: string | null;
  source_row_baseline?: number | null;
  source_row_candidate?: number | null;
  provenance: {
    candidate_observation_id?: string | null;
    candidate_submission_id?: string | null;
    baseline_observation_id?: string | null;
    baseline_submission_id?: string | null;
    identity_status?: string | null;
    admission_category?: string | null;
    supernumerary?: boolean | null;
  };
}

export interface SnapshotSummaryMetrics {
  CONTINUING?: number;
  ADDED?: number;
  WITHDRAWN?: number;
  DOCUMENTED_TRANSFER?: number;
  UNEXPLAINED_APPEARANCE?: number;
  UNEXPLAINED_DISAPPEARANCE?: number;
  AMBIGUOUS_IDENTITY?: number;
  INSUFFICIENT_EVIDENCE?: number;
  TOTAL_CANDIDATE?: number;
  TOTAL_BASELINE?: number;
  TOTAL_RECORDS?: number;
  // Computed categories
  LATERAL_ENTRY?: number;
  REGULAR_NEW_ADMISSIONS?: number;
  DEPARTED_TOTAL?: number;
  [key: string]: number | undefined;
}

export interface SnapshotComparisonResponse {
  candidate_snapshot_id: string;
  baseline_snapshot_id?: string | null;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  summary_metrics: SnapshotSummaryMetrics;
  records: ComparisonRecordItem[];
}

export interface SnapshotOption {
  id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  lifecycle_status: string;
  is_authoritative: boolean;
  declared_headcount: number;
  observed_headcount: number;
  snapshot_hash: string;
  created_at: string;
}

export interface UnifiedReconciliationResponse {
  reconciliation_run_id: string;
  snapshot_id: string;
  status: string;
  cohort_summary?: {
    summary_metrics: Record<string, number>;
    total_discrepancies: number;
  };
  intake_summary?: {
    regular_approved_intake: number;
    regular_enrolled_count: number;
    compliance_status: string;
  };
  duplicate_candidates?: Array<any>;
}
```

### 3.2 Duplicate Detection Contracts (`src/types/duplicate.ts`)
```typescript
export type DuplicateConflictType =
  | 'SIMULTANEOUS_ENROLMENT'
  | 'OVERLAPPING_ACTIVE_ROSTER'
  | 'UNAPPROVED_DUAL_PROGRAMME';

export interface DuplicateInstitutionEnrollment {
  institution_id: string;
  institution_name: string;
  institution_code: string;
  programme_id: string;
  programme_name: string;
  programme_code: string;
  academic_year: string;
  student_status: string;
  enrolled_date?: string | null;
  snapshot_id?: string | null;
  submission_id?: string | null;
  row_number?: number | null;
}

export interface DuplicateCandidateResponse {
  id: string; // duplicate record id or composite key
  student_identity_id: string;
  student_name: string;
  masked_apaar: string;
  apaar_blind_index?: string;
  academic_year: string;
  conflict_type: DuplicateConflictType;
  institution_a: DuplicateInstitutionEnrollment;
  institution_b: DuplicateInstitutionEnrollment;
  discrepancy_case_id?: string | null;
  discrepancy_case_number?: string | null;
  case_status?: string | null;
  detected_at?: string;
}

export interface RaiseDiscrepancyModalData {
  student_identity_id: string;
  student_name: string;
  masked_apaar: string;
  academic_year: string;
  institution_a: DuplicateInstitutionEnrollment;
  institution_b: DuplicateInstitutionEnrollment;
}
```

---

## 4. Cohort Explorer Component Design (`src/pages/CohortExplorer.tsx`)

### 4.1 Component Workflow & Conceptual Architecture
The Cohort Explorer resolves the classic regulatory blindspot where institutional student headcount remains unchanged (e.g. 60 students in 2023-24, 60 students in 2024-25), yet 8 students quietly dropped out and were replaced by unverified students.

```
+-----------------------------------------------------------------------------------+
|                            COHORT SELECTION BAR                                   |
| [Institution Dropdown] [Programme Dropdown] [Candidate R(t+1)] [Baseline R(t)]     |
| [Compare Cohorts Button] [Unified Reconciliation Run] [Export CSV]                |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                       VISUAL COHORT EVOLUTION CARDS                               |
| [Baseline N(t)]  ->  [Continued]  |  [Departed/Left]  |  [Transfers In]           |
|                      [Lateral]    |  [New Admissions] |  [Unexplained Delta]      |
|                      =====================================================        |
|                                     -> [Candidate N(t+1)]                         |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                    FILTER TABS & SEARCH (ALL | CONTINUING | ...)                  |
| [Search by name/roll/APAAR] [Category Filters] [Priority Badges]                  |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                    LONGITUDINAL STUDENT TRAJECTORY TABLE                          |
| Student | Masked APAAR | Baseline State | Candidate State | AICTE Audit Rationale |
| [View Timeline] [Open Case Dossier]                                               |
+-----------------------------------------------------------------------------------+
```

### 4.2 State Machine
The component manages the following reactive state:
1. **Context Selections**:
   - `selectedInstitutionId`: Scoped to `user.institution_id` for `INSTITUTION_ADMIN`. Changeable for `SYSTEM_ADMIN` / `REGULATORY_REVIEWER`.
   - `selectedProgrammeId`: Filtered by selected institution.
   - `candidateSnapshotId`: Selected candidate snapshot $R(t+1)$.
   - `baselineSnapshotId`: Selected baseline snapshot $R(t)$ or empty string (auto-resolve).
2. **Comparison Data**:
   - `comparison`: `SnapshotComparisonResponse | null`.
   - `loading`: boolean (while fetching comparison).
   - `error`: string | null.
3. **Execution State**:
   - `reconciling`: boolean (when executing formal `POST /reconciliation/runs` or `POST /reconciliation/unified`).
   - `reconcileSuccess`: string | null.
4. **Table Filters**:
   - `searchTerm`: string.
   - `activeTab`: `CohortDisplayCategory`.
   - `priorityFilter`: `'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'`.
5. **Timeline Modal State**:
   - `timelineStudentId`: string | null.
   - `timelineOpen`: boolean.

### 4.3 Visual Cohort Breakdown Mathematical Formulation
The metrics cards display:
- **Baseline Headcount $N(t)$**: Total students enrolled in baseline snapshot.
- **Continued ($C_t$)**: Classified as `CONTINUING` (enrolled in both $R(t)$ and $R(t+1)$).
- **Departed / Disappeared ($D_t$)**:
  - Legitimate Withdrawn: `WITHDRAWN` (graduated, formally withdrew).
  - Unexplained Disappearance: `UNEXPLAINED_DISAPPEARANCE` (missing without documentation).
- **Transferred In ($T_{in}$)**: `DOCUMENTED_TRANSFER` verified via destination transfer event.
- **Lateral Entry ($L_t$)**: `ADDED` with admission episode category `LATERAL_ENTRY` (joining directly in 2nd/3rd year).
- **New Admissions ($A_t$)**: `ADDED` with regular first-year admission episode.
- **Unexplained Appearances ($\Delta_{app}$)**: `UNEXPLAINED_APPEARANCE` on candidate roster without baseline or admission evidence.
- **Ambiguous Identity**: `AMBIGUOUS_IDENTITY` lacking valid APAAR format binding.
- **Candidate Headcount $N(t+1)$**:
  $$N(t+1) = C_t + T_{in} + L_t + A_t + \Delta_{app}$$

### 4.4 Detailed Component Layout Structure
1. **Header Section**:
   - Title: "Longitudinal Cohort Integrity Engine" with Signature Innovation badge (`#0D9488`).
   - Description emphasizing deterministic, non-punitive state tracking across annual roster versions.
2. **Control Strip**:
   - Responsive grid with Institution, Programme, Candidate Snapshot, and Baseline Snapshot selectors.
   - "Compare Cohorts" action button with Lucide `Layers` icon.
   - "Unified Reconcile" button triggering `POST /reconciliation/unified`.
   - "Export CSV" button calling `GET /snapshots/{candidateId}/compare/export?baseline_id={baselineId}&format=csv`.
3. **Summary KPI Cards Grid (6 Metric Cards)**:
   - Card 1: **Total Baseline vs Candidate** ($N_t \to N_{t+1}$ with percentage growth indicator).
   - Card 2: **Continuity Retention** (Count and % of cohort maintained).
   - Card 3: **New Cohort Intake** (Breakdown: Regular Admissions vs Lateral Entry).
   - Card 4: **Documented Inbound Transfers** (Legitimate mobility verified).
   - Card 5: **Cohort Departures** (Withdrawn vs Unexplained Disappearances).
   - Card 6: **Integrity Anomalies** (Unexplained Appearances + Ambiguous Identities).
4. **Trajectory Filter Tabs & Search**:
   - Full-text search by student name, roll number, or masked APAAR.
   - Segmented filter tabs with pill counters: All, Continuing, New Admissions, Lateral Entry, Transfers, Departed/Disappeared, Integrity Exceptions.
5. **Interactive Roster Observations Table**:
   - Columns: Student & Masked APAAR, Trajectory Classification Badge, Baseline Observation ($R(t)$), Candidate Observation ($R(t+1)$), Regulatory Audit Rationale, Action Button.
   - Action Button: "View Student Timeline" opens an in-page timeline drawer displaying student academic lifecycle.

---

## 5. Cross-Institution Duplicate Detection Component Design (`src/pages/DuplicateDetection.tsx`)

### 5.1 Component Workflow & Conceptual Architecture
Detects simultaneous concurrent enrollments across different universities using `apaar_blind_index` without decrypting the underlying database.

```
+-----------------------------------------------------------------------------------+
|                         DUPLICATE AUDIT CONTROL BAR                               |
| [Academic Year Selector (e.g. 2024-25)] [Search Filter] [Refresh Duplicate Index]  |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                           PRIVACY & AUDIT KPI STRIP                               |
| [Total Duplicate Conflicts] [Institutions Involved] [Discrepancies Raised]         |
| [Zero Full-DB Decryption: 100% HMAC-SHA256 Blind Indexing Privacy Assurance]      |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
|                DUAL-INSTITUTION COMPARATIVE SPLIT VIEW / CARDS                    |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | Student: Rohan Sharma | APAAR: XXXX-XXXX-4921 | Blind Index: hmac:4a9c...   |  |
|  +--------------------------------------+--------------------------------------+  |
|  | INSTITUTION A:                       | INSTITUTION B:                       |  |
|  | Apex Institute of Technology (APEX)  | National Polytechnic College (POLY)  |  |
|  | B.Tech Computer Science & Eng.       | Diploma Mechanical Engineering       |  |
|  | Year: 2024-25 | Status: ACTIVE       | Year: 2024-25 | Status: ACTIVE       |  |
|  | Observation Row: #14                 | Observation Row: #42                 |  |
|  +--------------------------------------+--------------------------------------+  |
|  | Diagnostic: Concurrent active enrollment across distinct institutions without|  |
|  | an approved dual-degree framework or transfer documentation.                |  |
|  | [View Existing Dossier / Raise Discrepancy Case]                            |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### 5.2 State Machine
1. **Filter State**:
   - `academicYear`: Default `'2024-25'`, configurable dropdown.
   - `searchTerm`: Search by student name or masked APAAR.
   - `statusFilter`: `'ALL' | 'UNRESOLVED' | 'UNDER_INVESTIGATION' | 'RESOLVED'`.
2. **Data State**:
   - `duplicates`: `DuplicateCandidateResponse[]`.
   - `loading`: boolean.
   - `error`: string | null.
3. **Discrepancy Action Modal**:
   - `raiseModalOpen`: boolean.
   - `activeDuplicate`: `DuplicateCandidateResponse | null`.
   - `initialReason`: string (mandatory minimum 10 characters).
   - `priority`: `'HIGH' | 'MEDIUM'`.
   - `submittingCase`: boolean.
4. **Dossier Investigation Integration**:
   - `dossierModalOpen`: boolean.
   - `selectedCase`: `DiscrepancyCase | null` (reusing `DiscrepancyDossierModal.tsx`).

### 5.3 Detailed Component Layout Structure
1. **Header Section**:
   - Title: "Cross-Institution Duplicate Detection" with Regulatory Shield icon.
   - Subtitle explaining concurrent enrollment detection via blind indexing.
   - Academic Year dropdown and Refresh button.
2. **KPI Summary Cards (4 Cards)**:
   - **Active Concurrent Conflicts** (total count).
   - **Distinct Institutions Involved** (count).
   - **Open Discrepancies Raised** (count of cases created).
   - **Privacy Integrity Status** (Green badge: "Blind Index Search Safe").
3. **Conflict Split Card View**:
   - Card Header:
     - Student Name with User icon.
     - Masked APAAR (`XXXX-XXXX-1234`) with Lock icon.
     - Blind Index Hash snippet (`hmac:9f8e...`) in monospace.
     - Academic Year badge.
     - Status badge: "Case Active (`DISC-2024-0012`)" or "Unresolved Conflict".
   - Split Institution Columns (Side-by-Side):
     - **Institution A**: Institution name, institution code badge, programme name & code, enrolment status, observation row number.
     - **Institution B**: Institution name, institution code badge, programme name & code, enrolment status, observation row number.
   - Regulatory Diagnostic Box:
     - Explainable rationale stating that the student is concurrently claimed as an active student by two independent institutions during the same academic year without an approved joint-degree framework or outbound transfer record.
   - Action Buttons:
     - If Discrepancy Case already exists: **"View Case Dossier"** button (fetches case and opens `DiscrepancyDossierModal`).
     - If no Discrepancy Case yet: **"Raise Discrepancy"** button (opens Raise Discrepancy Modal).
4. **Interactive Raise Discrepancy Modal**:
   - Provides structured input: Priority selection (`HIGH` / `MEDIUM`), Mandatory Justification Reason (min 10 chars with live character counter), and Submit action.
   - Automatically marks the duplicate conflict as raised upon submission and updates the UI state.

---

## 6. Implementation Blueprints

### 6.1 `src/types/cohort.ts`
```typescript
/**
 * Types for Longitudinal Cohort Integrity Engine.
 */
import { DiscrepancyClassification } from './discrepancy';

export type CohortDisplayCategory =
  | 'ALL'
  | 'CONTINUING'
  | 'NEW_ADMISSIONS'
  | 'LATERAL_ENTRY'
  | 'TRANSFERRED_IN'
  | 'DEPARTED'
  | 'UNEXPLAINED_APPEARANCE'
  | 'UNEXPLAINED_DISAPPEARANCE'
  | 'AMBIGUOUS_IDENTITY';

export interface ComparisonRecordItem {
  student_identity_id: string;
  internal_student_uuid: string;
  student_name: string;
  masked_apaar?: string | null;
  classification: DiscrepancyClassification;
  explanation: string;
  source_status_baseline?: string | null;
  source_status_candidate?: string | null;
  source_row_baseline?: number | null;
  source_row_candidate?: number | null;
  provenance: {
    candidate_observation_id?: string | null;
    candidate_submission_id?: string | null;
    baseline_observation_id?: string | null;
    baseline_submission_id?: string | null;
    identity_status?: string | null;
    admission_category?: string | null;
    supernumerary?: boolean | null;
  };
}

export interface SnapshotSummaryMetrics {
  CONTINUING?: number;
  ADDED?: number;
  WITHDRAWN?: number;
  DOCUMENTED_TRANSFER?: number;
  UNEXPLAINED_APPEARANCE?: number;
  UNEXPLAINED_DISAPPEARANCE?: number;
  AMBIGUOUS_IDENTITY?: number;
  INSUFFICIENT_EVIDENCE?: number;
  TOTAL_CANDIDATE?: number;
  TOTAL_BASELINE?: number;
  TOTAL_RECORDS?: number;
  [key: string]: number | undefined;
}

export interface SnapshotComparisonResponse {
  candidate_snapshot_id: string;
  baseline_snapshot_id?: string | null;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  summary_metrics: SnapshotSummaryMetrics;
  records: ComparisonRecordItem[];
}

export interface SnapshotItem {
  id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  completeness_status: string;
  lifecycle_status: string;
  is_authoritative: boolean;
  declared_headcount: number;
  observed_headcount: number;
  snapshot_hash: string;
  created_at: string;
}
```

### 6.2 `src/types/duplicate.ts`
```typescript
/**
 * Types for Cross-Institution Duplicate Detection.
 */
export type DuplicateConflictType =
  | 'SIMULTANEOUS_ENROLMENT'
  | 'OVERLAPPING_ACTIVE_ROSTER'
  | 'UNAPPROVED_DUAL_PROGRAMME';

export interface DuplicateInstitutionEnrollment {
  institution_id: string;
  institution_name: string;
  institution_code: string;
  programme_id: string;
  programme_name: string;
  programme_code: string;
  academic_year: string;
  student_status: string;
  enrolled_date?: string | null;
  snapshot_id?: string | null;
  submission_id?: string | null;
  row_number?: number | null;
}

export interface DuplicateCandidateResponse {
  id: string;
  student_identity_id: string;
  student_name: string;
  masked_apaar: string;
  apaar_blind_index?: string;
  academic_year: string;
  conflict_type: DuplicateConflictType;
  institution_a: DuplicateInstitutionEnrollment;
  institution_b: DuplicateInstitutionEnrollment;
  discrepancy_case_id?: string | null;
  discrepancy_case_number?: string | null;
  case_status?: string | null;
  detected_at?: string;
}
```

### 6.3 Route Updates in `src/App.tsx`
Replace the placeholders in `src/App.tsx` with:
```tsx
import { CohortExplorer } from './pages/CohortExplorer';
import { DuplicateDetection } from './pages/DuplicateDetection';

// ... Inside Enterprise Platform Routes ...
<Route path="duplicate-detection" element={<DuplicateDetection />} />
<Route path="cohort-explorer" element={<CohortExplorer />} />
```

---

## 7. Build Safety, Testing & Edge-Case Coverage

### 7.1 Multi-Tenant Isolation
- If `user.role === 'INSTITUTION_ADMIN'`, the institution dropdown is hidden or locked to `user.institution_name`. All requests automatically filter by `user.institution_id`.
- If `user.role === 'REGULATORY_REVIEWER'` or `'SYSTEM_ADMIN'`, the user can inspect any institution across India or evaluate cross-institution duplicate pairs.

### 7.2 Backend Fallback / Auto-Mocking for Smooth Demo
In development/demonstration mode, if `GET /api/v1/reconciliation/duplicates` has not returned data for the selected academic year, the component provides robust fallbacks and displays clear diagnostics instead of crashing or showing an unstyled white screen.

### 7.3 TypeScript Strict Mode Compliance
- Every property access checks for `null` and `undefined` guards (`item?.provenance?.admission_category`).
- Explicit return types on helper functions.
- Correct Axios generic response typing (`api.get<PaginatedSnapshotsResponse>(...)`).
- Verified zero unused variables.

---

## 8. Implementation Checklist for Worker Agent

| # | Task | Target File | Verification |
|---|------|-------------|--------------|
| 1 | Create `src/types/cohort.ts` | `src/types/cohort.ts` | `tsc --noEmit` |
| 2 | Create `src/types/duplicate.ts` | `src/types/duplicate.ts` | `tsc --noEmit` |
| 3 | Create `src/pages/CohortExplorer.tsx` | `src/pages/CohortExplorer.tsx` | Visual rendering, tab filtering, export CSV |
| 4 | Create `src/pages/DuplicateDetection.tsx` | `src/pages/DuplicateDetection.tsx` | Split card rendering, modal raise action |
| 5 | Update `src/App.tsx` to mount both pages | `src/App.tsx` | Routes active without `PlaceholderModule` |
| 6 | Execute Production Build | Shell command | `cmd /c npm run build` (0 errors) |
| 7 | Verify navigation in browser | `/app/cohort-explorer`, `/app/duplicate-detection` | Correct styling and layout |

---
*Report completed by Explorer M5.2-3. Handoff report prepared in `handoff.md`.*
