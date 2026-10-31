# APAAR SETU
# COMPLETE PRODUCT REQUIREMENTS DOCUMENT (PRD), SOFTWARE ARCHITECTURE AND AI DEVELOPMENT SPECIFICATION

**Project:** APAAR SETU  
**Full name:** Longitudinal Student Data Integrity & Verification Platform  
**Problem Statement ID:** SIH26263  
**Problem Statement:** Development of an APAAR ID-Based Student Data Management and Verification Platform for AICTE-Approved Institutions  
**Organisation:** AICTE  
**Department:** Regulation Bureau  
**Category:** Software  
**Theme:** Smart Automation  
**Development approach:** Full-stack web application  
**Project stage:** SIH 2026 prototype

---

# PART 1 — INSTRUCTIONS TO THE AI DEVELOPMENT AGENT

You are working as the principal software architect and development engineer for APAAR SETU.

You must understand this entire document before making architectural or implementation decisions.

You are responsible for helping develop a reliable, demonstrable, secure, modular, and visually polished software prototype.

Your responsibilities include:

- Software architecture.
- Frontend development.
- Backend development.
- Database design.
- API development.
- Business logic.
- Data validation.
- Reconciliation algorithms.
- Authentication and authorization.
- Security and privacy.
- Testing and debugging.
- UI/UX design.
- Deployment preparation.
- Documentation.

## Mandatory development instructions

1. Treat this document as the authoritative product specification.
2. Do not change the project's central purpose.
3. Do not turn APAAR SETU into a generic student management dashboard.
4. Preserve longitudinal cohort integrity as the signature innovation.
5. Implement the mandatory APAAR-based student management and verification capabilities.
6. Prioritise working functionality over decorative features.
7. Do not create buttons that do nothing.
8. Do not use hardcoded dashboard statistics when real application data is available.
9. Do not fabricate external API integrations.
10. Do not claim that simulated services are production integrations.
11. Never automatically label students or institutions fraudulent based solely on missing or conflicting information.
12. Maintain source submission history and correction history.
13. Use versioned and configurable validation rules.
14. Ensure important business logic is tested.
15. Use realistic synthetic datasets for the prototype.
16. Keep frontend, backend, database, and business logic properly separated.
17. Avoid unnecessary technologies and excessive abstraction.
18. Do not rewrite existing project files without first inspecting them.
19. Preserve existing working functionality unless there is a clear technical reason to change it.
20. Explain significant architectural decisions.

## Required working style

Work in development milestones.

For every milestone:

- Explain what is being built.
- Identify affected files.
- Explain database changes.
- Explain backend changes.
- Explain frontend changes.
- Implement the feature.
- Write tests.
- Run tests.
- Explain how to verify the feature.
- Report any incomplete functionality.

Never claim a feature is complete if it has not been implemented and tested.

If something is ambiguous, state the assumption before implementation.

---

# PART 2 — PRODUCT VISION

## 2.1 Product definition

APAAR SETU is an integrated APAAR-based student data management and verification platform designed for AICTE-approved institutions and authorised regulatory stakeholders.

The platform enables institutions to submit, update, validate, and manage student-level academic records using APAAR ID as a key academic identity reference.

It combines:

1. Secure institutional student data submission.
2. APAAR reference validation.
3. Student record management.
4. Admission and approved-intake reconciliation.
5. Cross-institution duplicate enrolment detection.
6. Longitudinal cohort integrity.
7. Historical aggregate-to-roster reconciliation.
8. Discrepancy investigation.
9. Authorised student record verification.
10. Certificate identity linkage.
11. Institutional and regulatory dashboards.
12. Reports, APIs, and audit trails.

## 2.2 Central innovation

The primary differentiator is the Longitudinal Cohort Integrity Engine.

The engine reconstructs how student cohorts evolve over successive academic years.

Instead of only checking whether the total number of students matches the declared enrolment, it compares the actual student-level identities and observations across different years.

It identifies:
- Continuing students.
- New appearances.
- Missing observations.
- Documented transfers.
- Unexplained appearances.
- Unexplained disappearances.
- Incomplete historical information.

It then compares these changes with documented admission and transfer events.

The system provides evidence-backed findings and makes uncertainty explicit.

## 2.3 Product promise

APAAR SETU does not merely check whether an APAAR ID exists.

It connects student identity references, institutional admissions, academic-year observations, and historical records to help establish a more complete and verifiable picture of student enrolment.

## 2.4 Two central pillars

### Pillar A: APAAR Student Data Management and Verification

This addresses the mandatory requirements of SIH26263.

It includes:
- Student repository.
- Data upload.
- Identity reference validation.
- Admission and intake checks.
- Cross-institution duplicate detection.
- Authorised verification.
- Reports.
- Dashboards.
- APIs.

### Pillar B: Longitudinal Cohort Integrity

This provides the signature differentiation.

It includes:
- Year-to-year student matching.
- Cohort continuity analysis.
- Transfer reconciliation.
- Unexplained cohort change detection.
- Historical aggregate comparison.
- Evidence-backed findings.
- Reproducible reconciliation reports.

Both pillars must be integrated into one application.

---

# PART 3 — USERS AND PERMISSIONS

The application must support role-based access control.

## 3.1 Institution Administrator

Can:
- View their institution dashboard.
- View authorised programmes.
- Upload student records.
- Update student records through controlled submissions.
- View validation errors.
- Run reconciliation.
- View cohort comparisons.
- Investigate their institution's discrepancies.
- Submit supporting evidence.
- Request corrections.
- Generate reports.

Cannot:
- Access other institutions' confidential student information.
- Change official regulatory rules.
- Alter original source submissions.
- View restricted system administration information.

## 3.2 AICTE / Regulatory Reviewer

Can:
- View authorised institution information.
- Monitor submissions.
- View institution and programme statistics.
- Review admission reconciliation.
- Review cross-institution conflicts.
- View cohort comparisons.
- Investigate discrepancy cases.
- Request additional evidence.
- Record decisions.
- Generate regulatory reports.

Cannot:
- Silently overwrite original institutional records.
- Access restricted information without appropriate permission.

## 3.3 System Administrator

Can:
- Manage institutions.
- Manage users.
- Assign roles.
- Manage programmes.
- Configure academic years.
- Configure applicable rules.
- Manage API clients.
- Review audit logs.
- Manage platform settings.

## 3.4 Student / External Verifier

Optional extensions.

Students may:
- View permitted personal record information.
- Challenge an incorrect institutional association.
- Submit correction requests.
- Track correction requests.

External authorised stakeholders may:
- Submit permitted verification requests.
- View permitted verification results.
- Verify certificate references.

Access must follow applicable consent, authorisation, and privacy requirements.

---

# PART 4 — APPLICATION NAVIGATION AND UI STRUCTURE

Build an enterprise-grade web application.

## 4.1 Main navigation

The left sidebar should contain:

1. Overview Dashboard.
2. Institution Management.
3. Student Repository.
4. Data Submissions.
5. APAAR Verification.
6. Admission Monitoring.
7. Cross-Institution Checks.
8. Cohort Explorer.
9. Reconciliation Centre.
10. Discrepancy Centre.
11. Review and Resolution.
12. Verification Portal.
13. Certificate Identity.
14. Reports and Analytics.
15. Rules and Configuration.
16. Audit and Access Management.

Navigation must be permission-aware.

Do not show institution administrators regulatory administration functions they are not authorised to use.

## 4.2 Overall design language

Design a modern enterprise SaaS application.

Visual direction:
- Primary colour: deep navy.
- Secondary colour: blue.
- Accent: teal.
- Background: off-white or light grey.
- Typography: Inter or a similar modern sans-serif.
- Sidebar: dark navy or clean light sidebar.
- Main content: spacious, clean layout.
- Cards: subtle borders and restrained shadows.
- Tables: professional and readable.
- Charts: minimal, meaningful, accessible.

Avoid:
- Excessive gradients.
- Excessive animations.
- Too many colours.
- Overcrowded dashboards.
- Decorative fake statistics.
- Unnecessary glassmorphism.
- Generic template-like interfaces.

The application must look like credible institutional software rather than a student project landing page.

## 4.3 Global interface components

Create reusable components:

- Application sidebar.
- Top navigation.
- User profile menu.
- Notification indicator.
- Institution selector.
- Programme selector.
- Academic-year selector.
- Search bar.
- Filter controls.
- KPI cards.
- Data tables.
- Status indicators.
- Confirmation dialogs.
- Empty states.
- Loading states.
- Error states.
- Toast notifications.
- Pagination.
- Breadcrumbs.
- Detail drawers.
- Modal forms.

All components should follow consistent design tokens.

---

# PART 5 — MODULE-BY-MODULE FUNCTIONAL SPECIFICATION

## MODULE 1: AUTHENTICATION AND ACCESS MANAGEMENT

### Purpose

Secure access to APAAR SETU.

### Required screens

- Login.
- Logout.
- User profile.
- User management.
- Role assignment.
- Password management.
- Access-denied page.

### Functional requirements

- Secure password storage.
- Session management.
- Role-based permissions.
- Institution-level access restriction.
- Backend permission enforcement.
- Login activity logging.
- Account activation/deactivation.

### Acceptance criteria

An institution administrator cannot access another institution's records by changing a URL, API parameter, or record ID.

Permissions must be checked on the backend, not merely by hiding frontend buttons.

---

## MODULE 2: INSTITUTION MANAGEMENT

### Purpose

Maintain structured institutional information.

### Data fields

- Institution UUID.
- Institution name.
- Institution code.
- Address.
- State.
- District.
- Institution category.
- Approval status.
- Contact details.
- Programmes.
- Creation date.
- Updated date.

### Features

- Register institution.
- Edit institution information.
- View institution details.
- Add programmes.
- Configure programme intake.
- Manage academic years.
- View institutional submissions.
- View institutional reconciliation history.

### Programme fields

- Programme ID.
- Programme name.
- Programme code.
- Qualification level.
- Approved intake.
- Applicable academic year.
- Approval reference.
- Programme status.

Approval information must be versioned by academic year.

---

## MODULE 3: STUDENT REPOSITORY

### Purpose

Maintain the structured student-level record system.

### Student identity data

- Internal student UUID.
- APAAR identifier reference.
- Masked APAAR ID.
- Student name.
- Date of birth, if required and authorised.
- Institution Student ID.
- Institution association.
- Programme.
- Academic status.

### Admission information

- Admission episode ID.
- Admission date.
- Academic year.
- Admission category.
- Programme.
- Approved intake reference.
- Supernumerary status.
- NRI status.
- OCI status.
- Foreign National status.
- Supporting source submission.

### Academic record information

- Academic-year observation.
- Current status.
- Transfer history.
- Withdrawal history.
- Graduation information, where available.
- Source submission reference.

### Important identity rules

Student identity and institution-specific admission episodes must be separate entities.

A student can have more than one admission episode over time.

A missing APAAR identifier must not automatically cause the system to discard the student record.

Similar names must not cause automatic identity merges.

A valid-looking APAAR format is not proof of actual identity verification.

---

## MODULE 4: DATA SUBMISSION AND IMPORT

### Purpose

Enable institutions to upload student-level information.

### Supported input formats

- CSV.
- XLSX.

### Submission workflow

1. Select institution.
2. Select programme.
3. Select academic year.
4. Select admission batch where applicable.
5. Upload file.
6. Detect column headers.
7. Map source columns to application fields.
8. Preview records.
9. Run validation.
10. Display record-level errors.
11. Allow correction or error download.
12. Confirm submission.
13. Save original source file.
14. Store parsed records.
15. Generate submission ID.

### Example import summary

- Total records: 500.
- Valid records: 470.
- Missing APAAR: 10.
- Duplicate identity references: 8.
- Missing required fields: 7.
- Potential conflicts: 5.

Counts must be calculated from the actual uploaded dataset.

### Import requirements

- Validate file type.
- Limit file size.
- Validate column mapping.
- Reject malicious or malformed files.
- Preserve original source file.
- Track submission version.
- Record uploader and timestamp.
- Avoid duplicate processing.
- Provide downloadable error report.

### Idempotency

Uploading the same submission twice must not silently duplicate student records.

Use a submission identifier and source fingerprint to recognise repeated imports.

---

## MODULE 5: APAAR VALIDATION

### Purpose

Validate the APAAR identity reference supplied in student records.

### Validation layers

1. Presence validation.
2. Format validation.
3. Duplicate reference detection.
4. Conflicting record detection.
5. External verification, only through an authorised integration when available.

### Result classifications

- Missing.
- Invalid format.
- Duplicate reference.
- Potential identity conflict.
- Format valid, authenticity unverified.
- Verified through authorised source.
- Verification unavailable.

The user interface must distinguish format validation from external identity verification.

Never display a format-valid identifier as externally verified.

---

## MODULE 6: ADMISSION AND INTAKE RECONCILIATION

### Purpose

Compare reported admissions with applicable approved intake information.

### Required information

- Approved intake.
- Actual enrolment.
- Admission category.
- Supernumerary seat classification.
- NRI status.
- OCI status.
- Foreign National status.
- Academic year.
- Programme approval reference.

### Validation logic

The engine must:

1. Identify the applicable institution and programme.
2. Load the correct approval configuration.
3. Load the applicable rule version.
4. Categorise student records.
5. Calculate applicable enrolment totals.
6. Apply the configured admission rule.
7. Compare results with the approved limits.
8. Generate an evidence-backed finding if necessary.

### Rule engine design

Do not hardcode one universal admission formula.

Rules must be configurable and versioned.

Each rule should contain:
- Rule ID.
- Version.
- Programme applicability.
- Academic-year applicability.
- Effective date.
- Required inputs.
- Calculation method.
- Policy reference.
- Validation result.

If required information is unavailable, return an insufficient-information state.

---

## MODULE 7: CROSS-INSTITUTION DUPLICATE DETECTION

### Purpose

Identify potentially conflicting student enrolments across institutions.

### Matching hierarchy

1. Verified APAAR identity reference.
2. Institution student identifiers, where meaningful.
3. Supporting student attributes for manual review.

### Detection example

The same verified identity appears in two institutions during overlapping active admission periods.

The system should:
- Identify the records.
- Compare institution associations.
- Compare programmes.
- Compare admission dates.
- Check documented transfer events.
- Check recognised concurrent enrolment conditions if configured.
- Generate a discrepancy case when unresolved.

### Required output

- Conflict ID.
- Matched student reference.
- Institution A.
- Institution B.
- Programme A.
- Programme B.
- Admission periods.
- Relevant events.
- Detection explanation.
- Review status.

A potential duplicate must not automatically become a fraud classification.

---

## MODULE 8: LONGITUDINAL COHORT INTEGRITY ENGINE

### Purpose

Reconstruct the evolution of student cohorts over academic years.

This is the signature innovation and highest-priority business logic.

### Inputs

- Historical student rosters.
- Current student roster.
- Student identity references.
- Admission events.
- Transfer events.
- Withdrawal events.
- Graduation events.
- Other configured recognised events.
- Source submission metadata.

### Core comparison

Let:

- R(t) represent the student roster for academic year t.
- R(t+1) represent the roster for the following academic year.

The engine compares the two populations.

### Expected classifications

1. Continuing students.
2. New appearances.
3. Missing observations.
4. Documented transfer-ins.
5. Documented transfer-outs.
6. Other explained movements.
7. Unexplained appearances.
8. Unexplained disappearances.
9. Ambiguous identity matches.
10. Insufficient historical evidence.

### Example

2024–25 CSE roster: 120 students.

2025–26 CSE roster: 120 students.

Second roster:
- 115 continuing students.
- 2 documented transfer-ins.
- 3 new appearances without recorded admission or transfer events.

The system identifies the three unexplained appearances.

It does not automatically call them fraudulent.

### Required interface

Display:
- Academic-year comparison.
- Total headcount.
- Continuing student count.
- New appearances.
- Missing observations.
- Transfer-ins.
- Transfer-outs.
- Unexplained changes.
- Uncertain cases.

Allow a reviewer to click an individual student and view their available academic timeline.

### Core matching rules

- Match verified identity references first.
- Use institution identifiers as supporting evidence.
- Handle missing identifiers separately.
- Keep ambiguous matches unresolved.
- Never automatically merge similar names.
- Reconcile observed changes with documented events.
- Account for incomplete historical source records.
- Preserve all source observations.

### Determinism

Identical source data, rule versions, and configuration must produce identical reconciliation results.

---

## MODULE 9: HISTORICAL AGGREGATE-TO-ROSTER RECONCILIATION

### Purpose

Compare aggregate historical declarations with detailed student-level rosters.

### Example

Previously declared aggregate enrolment: 120.

Detailed roster count: 116.

The system calculates a variance of four.

Before comparing, check:
- Institution.
- Programme.
- Academic period.
- Population definition.
- Student status definition.
- Counting methodology.
- Reporting source.

If the definitions differ, return a non-comparable result.

Do not automatically classify the variance as fraud or excess enrolment.

### Output

- Declared aggregate.
- Detailed roster count.
- Calculated variance.
- Comparability status.
- Source references.
- Explanation.
- Recommended review action.

---

## MODULE 10: DISCREPANCY CENTRE

### Purpose

Centralise all detected inconsistencies.

### Discrepancy categories

- Missing APAAR.
- Invalid APAAR format.
- Duplicate identity reference.
- Cross-institution conflict.
- Admission mismatch.
- Potential excess intake.
- Unexplained cohort appearance.
- Unexplained cohort disappearance.
- Transfer mismatch.
- Historical aggregate variance.
- Incomplete historical information.
- Conflicting student information.

### Case fields

- Case ID.
- Case type.
- Institution.
- Programme.
- Student reference.
- Academic year.
- Priority.
- Detection date.
- Source submission.
- Rule version.
- Explanation.
- Evidence.
- Review status.
- Assigned reviewer.

### Status values

- Open.
- Under review.
- Evidence requested.
- Awaiting institution response.
- Resolved.
- Insufficient evidence.
- Escalated.

### Interface

Create:
- Search.
- Filters.
- Priority indicators.
- Status filters.
- Case detail page.
- Evidence panel.
- Decision history.
- Reviewer assignment.

---

## MODULE 11: REVIEW AND RESOLUTION

### Purpose

Allow authorised humans to investigate findings.

### Reviewer actions

- Confirm discrepancy.
- Mark as legitimate transfer.
- Request evidence.
- Request correction.
- Mark insufficient evidence.
- Resolve after correction.
- Escalate.

### Decision requirements

Every decision must store:
- Reviewer.
- Decision.
- Reason.
- Timestamp.
- Supporting evidence.
- Previous status.
- New status.

Original source records must not be silently overwritten.

Corrections must generate new source versions or separate correction events.

---

## MODULE 12: AUTHORISED VERIFICATION PORTAL

### Purpose

Allow permitted stakeholders to verify student records.

### User inputs

- APAAR reference or permitted verification token.
- Institution reference where applicable.
- Verification purpose.

### Possible responses

- Record found.
- Record not found.
- Verification unavailable.
- Additional authorisation required.

Where authorised, display:
- Student reference.
- Institution.
- Programme.
- Academic status.
- Verification timestamp.
- Verification source.

### Security requirements

- Purpose limitation.
- Consent or other appropriate legal authorisation.
- Minimal disclosure.
- Rate limiting.
- Audit logging.
- Restricted data access.

Never expose full student records to unauthorised users.

---

## MODULE 13: CERTIFICATE IDENTITY LINKAGE

### Purpose

Demonstrate the display of APAAR ID alongside institution-issued student ID on certificates.

### Prototype features

- Sample certificate.
- Student name.
- Institution Student ID.
- APAAR ID.
- Certificate reference.
- QR code.
- Verification page.

The QR code must resolve to an actual verification route in the application.

The verification page must show only authorised information.

Use synthetic student and certificate data.

Do not claim that the prototype can issue or authenticate official university certificates.

---

## MODULE 14: INSTITUTION DASHBOARD

### KPI cards

- Total student records.
- Active enrolments.
- Reconciled records.
- Records requiring review.
- Potential identity conflicts.
- Pending submissions.

### Charts

- Programme-wise enrolment.
- Academic-year cohort trends.
- Admission versus approved intake.
- Discrepancy distribution.
- Submission history.

### Tables

- Recent submissions.
- Pending cases.
- Recent reconciliation runs.
- Programmes requiring attention.

All data must be sourced from the application database.

---

## MODULE 15: AICTE REGULATORY DASHBOARD

### KPI cards

- Total participating institutions.
- Total student records.
- Programmes monitored.
- Pending institutional submissions.
- Potential excess intake cases.
- Cross-institution conflicts.
- Unresolved discrepancies.

### Charts

- State-wise institutional submission coverage.
- Programme-wise enrolment.
- Approved intake versus reported enrolment.
- Historical cohort trends.
- Discrepancy trends.
- Institution-level reconciliation status.

### Filters

- State.
- Institution.
- Programme.
- Academic year.
- Admission category.
- Review status.

Only authorised aggregated or detailed information may be displayed.

---

## MODULE 16: REPORTS AND ANALYTICS

Generate:

1. Institutional enrolment report.
2. Programme-wise admission report.
3. APAAR validation report.
4. Duplicate identity report.
5. Cross-institution conflict report.
6. Cohort integrity report.
7. Admission reconciliation report.
8. Historical aggregate comparison.
9. Discrepancy investigation report.
10. Audit report.

### Export formats

- PDF.
- CSV.

### Reproducibility

Every report must record:
- Source submission IDs.
- Source versions.
- Reconciliation run ID.
- Rule versions.
- Configuration.
- Generation timestamp.

The system must be able to reproduce a historical report using the original source versions and rules.

---

## MODULE 17: RULES AND CONFIGURATION

Create a rule management module.

Administrators can configure:
- Academic years.
- Institutions.
- Programmes.
- Approved intake.
- Admission categories.
- Required fields.
- Recognised transfer events.
- Admission rules.
- Counting definitions.
- Rule effective dates.

Every rule must have version history.

Changing a rule must not silently change previously generated reports.

---

## MODULE 18: AUDIT AND ACTIVITY HISTORY

Track:
- Login activity.
- Data uploads.
- Record corrections.
- Reconciliation runs.
- Rule changes.
- Case creation.
- Reviewer decisions.
- Verification requests.
- Report generation.
- Permission changes.

Audit records should be append-only at the application level.

A hash or hash chain may be used as a tamper-evidence enhancement, but must not be presented as proof that the original data was true.

---

# PART 6 — DATA MODEL AND DATABASE ARCHITECTURE

Use PostgreSQL.

Design a relational database with the following entities.

## Core entities

### 1. institutions

- id
- institution_code
- name
- category
- approval_status
- address
- state
- district
- created_at
- updated_at

### 2. programmes

- id
- institution_id
- programme_code
- programme_name
- qualification_level
- status

### 3. approval_configurations

- id
- institution_id
- programme_id
- academic_year
- approved_intake
- approval_reference
- effective_from
- effective_to
- configuration_version

### 4. users

- id
- name
- email
- password_hash
- role_id
- institution_id
- status
- created_at

### 5. roles

- id
- role_name
- permissions

### 6. student_identities

- id
- internal_student_uuid
- encrypted_apaar_reference
- masked_apaar_reference
- identity_status
- created_at
- updated_at

### 7. institution_student_records

- id
- student_identity_id
- institution_id
- institution_student_id
- programme_id
- status
- created_at
- updated_at

### 8. admission_episodes

- id
- student_identity_id
- institution_id
- programme_id
- academic_year
- admission_date
- admission_category
- supernumerary_status
- nri_status
- oci_status
- foreign_national_status
- source_submission_id

### 9. annual_roster_observations

- id
- student_identity_id
- institution_id
- programme_id
- academic_year
- student_status
- source_submission_id
- source_record_id
- observation_timestamp

### 10. admission_events

- id
- student_identity_id
- institution_id
- programme_id
- event_type
- event_date
- evidence_reference
- source_submission_id

### 11. transfer_events

- id
- student_identity_id
- source_institution_id
- destination_institution_id
- source_programme_id
- destination_programme_id
- transfer_date
- verification_status
- evidence_reference

### 12. source_submissions

- id
- institution_id
- programme_id
- academic_year
- submission_type
- original_filename
- file_fingerprint
- version
- uploaded_by
- uploaded_at
- status

### 13. source_submission_records

- id
- submission_id
- source_row_number
- raw_record_reference
- parsed_record
- validation_status

### 14. rule_definitions

- id
- rule_code
- name
- description
- rule_category

### 15. rule_versions

- id
- rule_definition_id
- version
- configuration
- effective_from
- effective_to
- source_reference

### 16. reconciliation_runs

- id
- institution_id
- programme_id
- start_academic_year
- end_academic_year
- source_submission_ids
- rule_version_ids
- status
- started_at
- completed_at

### 17. reconciliation_findings

- id
- reconciliation_run_id
- student_identity_id
- finding_type
- priority
- explanation
- evidence_reference
- uncertainty_state
- status

### 18. review_cases

- id
- finding_id
- assigned_reviewer_id
- case_status
- created_at
- updated_at

### 19. review_decisions

- id
- review_case_id
- reviewer_id
- decision
- reason
- supporting_evidence
- created_at

### 20. correction_events

- id
- source_submission_id
- corrected_submission_id
- correction_reason
- corrected_by
- created_at

### 21. evidence_references

- id
- source_type
- source_id
- description
- evidence_metadata
- created_at

### 22. audit_events

- id
- actor_id
- action
- entity_type
- entity_id
- timestamp
- metadata

Database requirements:

- Use UUID primary keys.
- Add foreign-key constraints.
- Add appropriate indexes.
- Use transactions.
- Store timestamps consistently.
- Use migrations.
- Avoid unnecessary duplication.
- Maintain institution-level isolation.
- Keep source data and derived findings separate.

The exact schema may be refined during implementation, but these domain concepts must remain represented.

---

# PART 7 — BACKEND ARCHITECTURE

Recommended backend stack:

- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- Alembic.
- PostgreSQL.
- Pytest.

Use a modular architecture.

Suggested structure:

backend/
  app/
    main.py
    core/
      config.py
      security.py
      permissions.py
    api/
      dependencies.py
      routes/
        auth.py
        institutions.py
        programmes.py
        students.py
        submissions.py
        validation.py
        admission.py
        duplicate_detection.py
        cohort.py
        reconciliation.py
        discrepancies.py
        reviews.py
        verification.py
        reports.py
        rules.py
        audit.py
    models/
    schemas/
    services/
      identity_service.py
      import_service.py
      validation_service.py
      admission_service.py
      duplicate_service.py
      cohort_service.py
      reconciliation_service.py
      discrepancy_service.py
      review_service.py
      verification_service.py
      report_service.py
      audit_service.py
    repositories/
    integrations/
      apaar_adapter.py
      aicte_adapter.py
    tests/

Do not place all business logic in API route functions.

Keep algorithms testable independently of HTTP requests.

---

# PART 8 — API SPECIFICATION

Use REST APIs with versioned routes.

Base path:

/api/v1

## Authentication

POST /auth/login

POST /auth/logout

GET /auth/me

## Institutions

GET /institutions

POST /institutions

GET /institutions/{institution_id}

PATCH /institutions/{institution_id}

## Programmes

GET /institutions/{institution_id}/programmes

POST /programmes

GET /programmes/{programme_id}

## Students

GET /students

POST /students

GET /students/{student_id}

PATCH /students/{student_id}

GET /students/{student_id}/timeline

## Submissions

POST /submissions/upload

GET /submissions

GET /submissions/{submission_id}

GET /submissions/{submission_id}/preview

GET /submissions/{submission_id}/errors

POST /submissions/{submission_id}/confirm

## Validation

POST /validation/run

GET /validation/{validation_run_id}

## Admission

POST /admission/reconcile

GET /admission/results

## Cross-institution checks

POST /duplicate-detection/run

GET /duplicate-detection/cases

## Cohort

POST /cohort/compare

GET /cohort/compare/{run_id}

GET /cohort/student/{student_id}/timeline

## Reconciliation

POST /reconciliation/run

GET /reconciliation/runs

GET /reconciliation/runs/{run_id}

GET /reconciliation/runs/{run_id}/findings

## Discrepancies

GET /discrepancies

GET /discrepancies/{case_id}

PATCH /discrepancies/{case_id}

## Review

POST /reviews/{case_id}/decisions

GET /reviews/{case_id}/history

## Verification

POST /verification/request

GET /verification/{verification_id}

## Reports

POST /reports/generate

GET /reports

GET /reports/{report_id}

## Rules

GET /rules

POST /rules

GET /rules/{rule_id}/versions

POST /rules/{rule_id}/versions

## Audit

GET /audit/events

All routes must implement authentication, permission checks, input validation, and appropriate error responses.

Use pagination for large collections.

Never expose unrestricted student data through a public endpoint.

---

# PART 9 — FRONTEND ARCHITECTURE

Recommended stack:

- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- React Router.
- TanStack Query or equivalent.
- Recharts.
- Axios or equivalent.

Suggested structure:

frontend/
  src/
    app/
    components/
      layout/
      navigation/
      tables/
      charts/
      forms/
      cards/
      dialogs/
      feedback/
    pages/
      Login/
      Dashboard/
      Institutions/
      StudentRepository/
      Submissions/
      APAARVerification/
      AdmissionMonitoring/
      DuplicateDetection/
      CohortExplorer/
      Reconciliation/
      Discrepancies/
      Reviews/
      VerificationPortal/
      Certificates/
      Reports/
      Rules/
      Audit/
    features/
    hooks/
    services/
    types/
    utils/
    styles/

Frontend requirements:

- Responsive layout.
- Role-based navigation.
- API-driven data.
- Reusable components.
- Loading states.
- Empty states.
- Error states.
- Form validation.
- Search and filters.
- Pagination.
- Accessible colour contrast.
- Clear feedback after actions.

Do not hardcode all data inside React components.

The backend is the source of truth.

---

# PART 10 — SYNTHETIC DATA AND DEMO ENVIRONMENT

Create a synthetic dataset containing:

- At least 3 institutions.
- At least 3 programmes.
- 3 consecutive academic years.
- Approximately 300–500 student records.
- Multiple admission batches.
- Different admission categories.
- Transfers.
- Withdrawals.
- Duplicate identity references.
- Missing APAAR identifiers.
- Incomplete historical rosters.
- Unexplained cohort appearances.
- Similar-name cases.
- Historical aggregate declarations.

Create realistic but entirely fictional Indian names and institution names.

Do not use actual personal student information.

Clearly identify the dataset as synthetic.

## Mandatory main demonstration scenario

Institution A:

Programme: Computer Science and Engineering.

2024–25 roster: 120 students.

2025–26 roster: 120 students.

The later roster contains:

- 115 continuing students.
- 2 documented transfer-in students.
- 3 new appearances without recorded admission or transfer events.

Expected output:

- Headcount remains 120.
- The system recognises 115 continuing students.
- The system recognises 2 documented transfer-ins.
- The system flags 3 unexplained appearances.
- The system does not automatically classify those three as fraud.

Also include a legitimate transfer-out and an incomplete historical roster.

This scenario must work through the actual application, not merely be represented by static screenshots.

---

# PART 11 — SECURITY, PRIVACY AND COMPLIANCE

Treat student records as sensitive information.

Implement:

- Secure password hashing.
- Role-based access control.
- Institution-level data isolation.
- Backend permission enforcement.
- Masked APAAR identifiers.
- Restricted identity access.
- Secure session management.
- File upload validation.
- Audit logs.
- Rate limiting for verification endpoints.
- Input sanitisation.
- Environment-based secrets.
- TLS in deployment.
- Appropriate encryption at rest.
- Minimal data disclosure.
- Consent or other valid authorisation for external verification.

Do not collect raw Aadhaar or biometric data.

Do not claim legal compliance merely because a security feature exists.

Document production security requirements separately from prototype functionality.

---

# PART 12 — TESTING AND QUALITY ASSURANCE

Use Pytest for backend tests and appropriate frontend testing tools.

## Mandatory backend tests

1. Valid student record creation.
2. Missing APAAR reference.
3. Invalid APAAR format.
4. Duplicate APAAR reference.
5. Duplicate submission.
6. Valid student roster upload.
7. Invalid upload file.
8. Continuing student matching.
9. New unexplained appearance.
10. Documented transfer-in.
11. Documented transfer-out.
12. Incomplete historical roster.
13. Ambiguous identity match.
14. Similar names must not be merged.
15. Cross-institution duplicate detection.
16. Comparable aggregate variance.
17. Non-comparable aggregate baseline.
18. Admission rule validation.
19. Unsupported rule configuration.
20. Corrected source submission.
21. Deterministic reconciliation rerun.
22. Reviewer decision history.
23. Institution-level access restrictions.
24. Unauthorized modification rejection.
25. Audit event creation.

## Required frontend tests

- Login and role-based navigation.
- Upload flow.
- Column mapping.
- Preview and validation.
- Dashboard rendering.
- Cohort filters.
- Discrepancy details.
- Review decision submission.
- Report export.
- Error and empty states.

## Definition of done

A module is complete only when:

1. Its interface exists.
2. Its backend logic works.
3. Its data is persisted appropriately.
4. Permissions are enforced.
5. Error handling works.
6. Automated tests pass.
7. The feature has been manually verified.
8. Its limitations are documented.

---

# PART 13 — DEVELOPMENT MILESTONES

Follow this exact order.

## Milestone 0 — Existing project inspection

- Inspect current files.
- Inspect dependencies.
- Inspect architecture.
- Identify working functionality.
- Identify missing functionality.
- Report technical debt.
- Recommend the next changes.

Do not rewrite the project.

## Milestone 1 — Foundation

- Frontend shell.
- Backend application.
- PostgreSQL.
- Database migrations.
- Authentication.
- Roles.
- Institution and programme management.

## Milestone 2 — Student repository

- Student identity.
- Institution-specific records.
- Admission episodes.
- Academic-year observations.
- Student timeline.

## Milestone 3 — Data submission

- CSV upload.
- XLSX upload.
- Column mapping.
- Preview.
- Validation.
- Versioned submissions.
- Error reports.
- Idempotent imports.

## Milestone 4 — APAAR and admission validation

- APAAR format validation.
- Duplicate reference detection.
- Admission categories.
- Approved intake configuration.
- Admission reconciliation.
- Rule versioning.

## Milestone 5 — Cross-institution detection

- Identity matching.
- Overlapping admission detection.
- Transfer reconciliation.
- Discrepancy creation.

## Milestone 6 — Cohort integrity engine

- Historical roster matching.
- Continuing student identification.
- New appearances.
- Missing observations.
- Transfer recognition.
- Unexplained changes.
- Uncertainty handling.
- Cohort comparison reports.

## Milestone 7 — Investigation

- Discrepancy centre.
- Case assignments.
- Reviewer decisions.
- Evidence requests.
- Corrections.
- Audit history.

## Milestone 8 — Dashboards and reporting

- Institution dashboard.
- AICTE dashboard.
- Analytics.
- Reports.
- PDF and CSV export.

## Milestone 9 — Verification and certificate linkage

- Authorised verification workflow.
- Simulated integration adapters.
- Certificate demonstration.
- QR verification.

## Milestone 10 — Final SIH demo preparation

- Synthetic demo dataset.
- End-to-end testing.
- UI polish.
- Performance checks.
- Security checks.
- Demo walkthrough.
- Presentation screenshots.

---

# PART 14 — FINAL ACCEPTANCE SCENARIOS

The completed prototype must successfully demonstrate all of these:

### Scenario A: Student data submission

An institution uploads a roster. The platform maps columns, validates fields, identifies errors, and stores a versioned submission.

### Scenario B: APAAR reference validation

The system identifies missing and incorrectly formatted APAAR references without falsely claiming external verification.

### Scenario C: Admission excess detection

A programme's reported admissions exceed its configured applicable intake limit. The system explains the calculation and generates a discrepancy.

### Scenario D: Cross-institution conflict

The same verified identity reference appears in conflicting active institutional records. The system detects the conflict and creates a review case.

### Scenario E: Same-count cohort substitution

Two academic-year rosters have the same headcount but different student compositions. The engine identifies unexplained appearances.

### Scenario F: Legitimate transfer

A documented transfer is recognised and does not incorrectly become an unexplained cohort change.

### Scenario G: Insufficient historical evidence

Historical information is incomplete. The engine returns an uncertainty classification.

### Scenario H: Human review

A reviewer examines a case, records a reasoned decision, and preserves the original submission.

### Scenario I: Reproducible reporting

The same source submissions and rule versions reproduce the same reconciliation result.

### Scenario J: Authorised verification

A permitted stakeholder accesses a verification route and sees only the information they are authorised to receive.

---

# PART 15 — NON-GOALS AND FEATURES TO AVOID

Do not prioritise:

- Blockchain as a core feature.
- Facial recognition.
- Biometric authentication.
- Generic AI chatbots.
- Social networking.
- Student entertainment features.
- Unnecessary mobile applications.
- A nationwide live database without authorised infrastructure.
- Fake integrations with APAAR or AICTE.
- Unexplained AI fraud scoring.
- Excessive animations.
- Decorative dashboard statistics.

The product must remain focused on institutional student data integrity and verification.

---

# PART 16 — FINAL PRODUCT POSITIONING

APAAR SETU is an integrated APAAR-based student data management and verification platform for AICTE-approved institutions.

It combines student-level data submission, identity-reference validation, admission reconciliation, cross-institution duplicate detection, authorised verification, and regulatory analytics with a longitudinal cohort integrity engine.

Its distinguishing capability is the ability to reconstruct how institutional student cohorts change across academic years, reconcile those changes against documented events, and identify unexplained discrepancies that may remain hidden even when aggregate enrolment totals appear unchanged.

The platform provides evidence-backed findings, uncertainty-aware classification, human review, and reproducible reports.

The objective is to strengthen the completeness, consistency, authenticity, and verifiability of institutional academic student records.

---

# FINAL DIRECTIVE

Build APAAR SETU as one integrated, functional application.

The highest-priority capabilities are:

1. Student repository and identity references.
2. Secure student data submission.
3. APAAR validation.
4. Admission and intake reconciliation.
5. Cross-institution duplicate detection.
6. Longitudinal cohort integrity.
7. Evidence-backed discrepancy investigation.
8. Institution and AICTE dashboards.

The Cohort Integrity Engine is the signature innovation, but the mandatory APAAR student data management and verification workflow must work as well.

Preserve the product scope.

Do not invent features to make the application look more impressive.

Do not sacrifice correctness for visual appearance.

Every important result must be explainable, traceable, testable, and reproducible.