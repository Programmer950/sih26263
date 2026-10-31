# APAAR SETU — API Contracts Specification (`/api/v1`)

**Document Version:** 1.1.0  
**Status:** Approved Architecture Draft  
**Standard:** OpenAPI 3.1 / JSON Schema Compliant  
**Base URL:** `/api/v1`  
**Authentication Scheme:** `Bearer <JWT>` (in `Authorization` header)  

---

## 1. Global Standards & Error Envelopes

### 1.1 Standard Success Response Envelope
Paginated endpoints conform to the standard structure:
```json
{
  "items": [],
  "total": 120,
  "page": 1,
  "limit": 50,
  "pages": 3
}
```

### 1.2 Standard Error Response Envelope
```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "The requested submission was not found.",
    "details": {},
    "timestamp": "2026-10-30T10:30:00Z",
    "request_id": "req_01h7..."
  }
}
```

---

## 2. Authentication & Session Revocation (`/auth`)

### `POST /api/v1/auth/login`
Authenticates user using Argon2id verification and returns JWT access & refresh tokens.
- **Request Body:**
  ```json
  {
    "email": "admin@apex.edu.in",
    "password": "SecurePassword123!"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "def5020...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "b18f50c2-5e64-4e78-b19e-e090f7d4c82b",
      "name": "Prof. R. Sharma",
      "email": "admin@apex.edu.in",
      "role": "INSTITUTION_ADMIN",
      "institution_id": "0192e2b3-8fa0-7e11-9a74-d4b8fbc4e891",
      "permissions": ["upload_data", "view_reports", "run_reconciliation"]
    }
  }
  ```

### `GET /api/v1/auth/me`
Retrieves current session context and permission scope.
- **Headers:** `Authorization: Bearer <token>`
- **Response `200 OK`:** User profile JSON matching login response.

### `POST /api/v1/auth/logout`
Revokes the current session token immediately by recording the `jti` in `session_revocations`.
- **Headers:** `Authorization: Bearer <token>`
- **Response `200 OK`:**
  ```json
  { "success": true, "message": "Session successfully terminated and token revoked." }
  ```

---

## 3. Submissions, Records & Snapshots (`/submissions`, `/snapshots`)

### `POST /api/v1/submissions/upload` (Operation A: Secure Upload & Initial Inspection)
Uploads an untrusted student roster file (CSV or XLSX) with streaming SHA-256 fingerprinting, database-enforced idempotency checks, pre-flight archive inspections, and safe isolated preview generation.
- **Tenancy Enforcement:** `institution_id` is automatically bound from user claims for `INSTITUTION_ADMIN`. For `REGULATORY_REVIEWER`, `institution_id` must be explicitly provided and authorized.
- **Security Invariant:** Client filename is ignored for storage; a randomized UUID key (`uploads/{uuid}.dat`) is used with restricted permissions.
- **Headers:** `Authorization: Bearer <token>`, `Idempotency-Key: <client_key>` (optional)
- **Form Data:**
  - `file`: binary (CSV or XLSX, $\le 10\text{ MB}$, max 25,000 rows, max 50 cols)
  - `institution_id`: UUID (optional if institution admin)
  - `programme_id`: UUID (verified via composite relation to belong to target institution)
  - `academic_year`: string (e.g. `"2024-25"`)
  - `submission_type`: string (`"ANNUAL_ROSTER"`, `"ADMISSION_BATCH"`, `"CORRECTION"`)
- **Idempotency & Deduplication Logic:**
  1. Computes raw byte SHA-256 fingerprint while streaming.
  2. If `Idempotency-Key` is provided:
     - Queries `source_submissions` for `(institution_id, client_idempotency_key)`.
     - **Same Key + Same Request** (matching programme, academic year, submission type, and file fingerprint): returns original submission preview response (idempotent replay).
     - **Same Key + Different Request** (differing context or file fingerprint): rejects with `409 Conflict`.
  3. Contextual file content check via `UNIQUE(institution_id, programme_id, academic_year, submission_type, file_fingerprint)`:
     - If identical file is already `COMMITTED` in same context: rejects with `409 Conflict`.
     - If identical file submitted for different programme or academic year: accepted cleanly.
- **Lifecycle Transition:** `None` $\to$ `UPLOADED` $\to$ `VALIDATING` $\to$ `PREVIEW_READY`.
- **Response `201 Created`:**
  ```json
  {
    "submission_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "submission_status": "PREVIEW_READY",
    "file_fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "original_filename": "Apex_CSE_2024_25.csv",
    "file_size_bytes": 48201,
    "total_rows_count": 120,
    "valid_rows_count": 115,
    "warning_rows_count": 3,
    "error_rows_count": 0,
    "duplicate_rows_count": 2,
    "detected_headers": ["student_id", "full_name", "apaar_id", "student_status", "admission_date"],
    "suggested_mapping": {
      "student_id": "student_id",
      "full_name": "full_name",
      "apaar_id": "apaar_id",
      "student_status": "student_status"
    },
    "sample_rows": [
      {
        "row_number": 1,
        "raw_payload": { "student_id": "CSE-001", "full_name": "Aditya Verma", "apaar_id": "123456789012" },
        "validation_status": "VALID",
        "errors": [],
        "warnings": []
      },
      {
        "row_number": 14,
        "raw_payload": { "student_id": "CSE-014", "full_name": "Pooja Sharma", "apaar_id": "12345" },
        "validation_status": "WARNING",
        "errors": [],
        "warnings": ["Invalid APAAR format: expected 12 numeric digits. Retained as unverified reviewable identity."]
      }
    ]
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: File exceeds 10MB, column limit exceeded, zip-bomb decompression ratio exceeded, or unparseable format.
  - `403 Forbidden`: Institution Admin attempting upload for another institution.
  - `409 Conflict`: Idempotency key conflict or contextual duplicate detected that is already `COMMITTED`.

---

### `POST /api/v1/submissions/{id}/preview` (Operation B: Full-File Mapping Preview & Version Binding)
Executes full-file validation across all rows of the stored file against a proposed column mapping, computing complete error/warning breakdowns without mutating the student repository. Creates a persistent, immutable preview version.
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "column_mapping": {
      "student_id": "student_id",
      "full_name": "full_name",
      "apaar_id": "apaar_id",
      "student_status": "student_status"
    }
  }
  ```
- **Behavior:**
  1. Verifies submission exists, belongs to caller's tenant, and is in `PREVIEW_READY` state.
  2. Scans *every* row in the stored file (identifying errors beyond the first 50 rows).
  3. Deactivates previous previews for this submission.
  4. Generates an immutable `submission_previews` record with:
     - `preview_id` (UUID)
     - `file_fingerprint` (must match current file)
     - `column_mapping` (JSONB)
     - `mapping_version` (`v1.0`)
     - `mapping_hash` (SHA-256 of canonical sorted mapping JSON)
     - `validation_summary` (full-file counts)
     - `created_at` (timestamp)
  5. **Zero Repository Mutations:** Does NOT insert or modify `student_identities`, `institution_student_records`, `annual_roster_observations`, or `roster_snapshots`.
- **Response `200 OK`:**
  ```json
  {
    "preview_id": "8c3b2e10-4567-89ab-cdef-0123456789ab",
    "submission_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "file_fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "mapping_version": "v1.0",
    "mapping_hash": "b47c1f2e8a9d0c3f4e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e",
    "total_rows_count": 120,
    "valid_rows_count": 115,
    "warning_rows_count": 3,
    "error_rows_count": 2,
    "duplicate_rows_count": 0,
    "validation_summary": {
      "errors_by_row": [{"row_number": 55, "error": "Missing mandatory student identifier"}],
      "warnings_by_row": [{"row_number": 14, "warning": "Invalid APAAR format: non-numeric"}]
    },
    "created_at": "2026-10-30T11:00:00Z"
  }
  ```

---

### `POST /api/v1/submissions/{id}/confirm` (Operation C: Atomic Transactional Ingestion)
Commits the submission in an **atomic transactional operation** bound strictly to an immutable preview version:
- **Execution Flow:**
  1. Verifies caller possesses tenant authority.
  2. Acquires row lock `SELECT ... FOR UPDATE` on `source_submissions` row to serialize concurrent confirmation requests.
  3. **Preview Version Binding & Pre-Ingestion Revalidation:**
     - Verifies `preview_id` is supplied, exists, belongs to this submission, and is active.
     - Verifies `preview.file_fingerprint` matches `submission.file_fingerprint`.
     - Verifies supplied `column_mapping` computes the exact identical `mapping_hash`.
     - **Rejection on Stale or Changed Preview:** If the mapping was modified or does not match `mapping_hash`, rejects with `409 Conflict` ("Stale or mismatched preview version. A new preview must be generated for modified column mappings.").
     - Revalidates the stored original file using the exact confirmed mapping.
  4. **Ingestion Transaction Begins:**
     - Parses all rows from the securely stored file.
     - Preserves raw evidence verbatim in `source_submission_records` (raw payloads unmutated; formula metadata recorded).
     - Global Identity Resolution:
       - Valid 12-digit APAAR: looks up via HMAC blind index. If found, links identity. If not found, attempts `INSERT` into `student_identities`. If concurrent conflict occurs on `uq_student_identities_apaar_blind_index`, catches conflict and retrieves existing identity.
       - Missing or malformed APAAR: creates provisional `StudentIdentity` (`identity_status = 'MISSING_APAAR'`).
       - Weak attributes (same name without APAAR) **never** merge identities.
     - Binds `InstitutionStudentRecord` for the student within caller's institution.
     - Appends versioned `annual_roster_observations` referencing `source_submission_id` and `source_record_id` via dual composite foreign keys (context and record integrity).
     - Creates `roster_snapshots` record with canonical hash (`v1-sha256-sorted-uuids`), `declared_headcount`, and `observed_headcount`.
     - If `mark_as_authoritative = true`, serializes via advisory lock and updates snapshot pointers atomically.
     - Chained SHA-256 audit event logged.
     - Sets `submission_status = 'COMMITTED'`, `committed_at = NOW()`.
     - Commits transaction.
  5. **Dual-Transaction Failure Handling:**
     - If any unhandled exception or constraint failure occurs during step 4, the entire ingestion transaction is immediately rolled back. All created student records and observations are cleanly erased.
     - In a **separate, isolated database transaction**, updates `source_submissions` setting `submission_status = 'FAILED'` and recording a sanitized `failure_reason`.
- **Request Body:**
  ```json
  {
    "preview_id": "8c3b2e10-4567-89ab-cdef-0123456789ab",
    "column_mapping": {
      "student_id": "student_id",
      "full_name": "full_name",
      "apaar_id": "apaar_id",
      "student_status": "student_status"
    },
    "completeness_status": "COMPLETE",
    "mark_as_authoritative": true
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "submission_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "submission_status": "COMMITTED",
    "snapshot_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "total_records_processed": 120,
    "valid_records": 115,
    "warning_records": 3,
    "error_records": 0,
    "snapshot_status": "ACTIVE",
    "completeness_status": "COMPLETE",
    "is_authoritative": true,
    "committed_at": "2026-10-30T10:45:00Z"
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Submission not in `PREVIEW_READY` state.
  - `409 Conflict`: Submission was already committed or a concurrent confirmation request is already processing.

---

### `POST /api/v1/submissions/{id}/cancel`
Cancels an uncommitted submission, preserving original evidence while preventing future ingestion.
- **Behavior:**
  - Sets `submission_status = 'CANCELLED'`, `cancelled_at = NOW()`, `cancelled_by_user_id = current_user.id`.
  - **Evidence Retention:** The original uploaded file is permanently retained in `backend/uploads/` for regulatory auditability; only temporary parser cache files are pruned.
  - Any subsequent call to `/confirm` on this submission returns `400 Bad Request`.
- **Response `200 OK`:**
  ```json
  { "submission_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "submission_status": "CANCELLED" }
  ```

---

### `GET /api/v1/submissions`
Lists submissions scoped to caller's institution (or across all institutions for AICTE regulatory reviewers).

---

### `GET /api/v1/submissions/{id}`
Retrieves detailed submission information including counts, mapping configuration, validation summary, and processing timestamps.

---

### `GET /api/v1/snapshots`
Lists roster snapshots filtered by institution, programme, and academic year.
- **Query Params:** `institution_id`, `programme_id`, `academic_year`, `is_authoritative`
- **Response `200 OK`:**
  ```json
  [
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "institution_id": "0192e2b3-8fa0-7e11-9a74-d4b8fbc4e891",
      "programme_id": "d04e76d9-81a6-4a41-b8eb-991f82f2c8d2",
      "academic_year": "2024-25",
      "source_submission_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "completeness_status": "COMPLETE",
      "lifecycle_status": "ACTIVE",
      "is_authoritative": true,
      "declared_headcount": 120,
      "observed_headcount": 120,
      "snapshot_canonicalization_version": "v1-sha256-sorted-uuids",
      "snapshot_hash": "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
      "effective_from": "2026-10-30T10:45:00Z",
      "created_at": "2026-10-30T10:45:00Z"
    }
  ]
  ```

---

### `POST /api/v1/snapshots/{id}/mark-authoritative`
Atomically marks a snapshot as authoritative for its `(institution_id, programme_id, academic_year)`.
- **Pre-Flight Authorization & Eligibility Guards:**
  1. Acquires transaction-level advisory lock:
     `SELECT pg_advisory_xact_lock(hashtext('snap_' || institution_id::text || '_' || programme_id::text || '_' || academic_year));`
  2. Verifies caller's tenancy authorization (an Institution Admin can only promote within their own institution).
  3. Verifies target snapshot matches target context `(institution_id, programme_id, academic_year)`.
  4. Verifies target snapshot is eligible for promotion (`lifecycle_status = 'ACTIVE'`, and source submission is `COMMITTED`).
- **Atomic Transactional Transition:**
  - Demotes existing authoritative snapshot:
    `UPDATE roster_snapshots SET is_authoritative = FALSE, lifecycle_status = 'SUPERSEDED', superseded_by_snapshot_id = :id, superseded_at = NOW() WHERE institution_id = :inst_id AND programme_id = :prog_id AND academic_year = :year AND is_authoritative = TRUE;`
  - Promotes target snapshot:
    `UPDATE roster_snapshots SET is_authoritative = TRUE, lifecycle_status = 'ACTIVE' WHERE id = :id;`
  - If any error occurs, transaction rolls back leaving previous authoritative snapshot completely unchanged.
- **Response `200 OK`:**
  ```json
  {
    "snapshot_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "is_authoritative": true,
    "lifecycle_status": "ACTIVE",
    "completeness_status": "COMPLETE",
    "demoted_snapshot_id": "4b8e21a0-1234-5678-90ab-cdef12345678"
  }
  ```

---

## 4. Longitudinal Cohort Integrity Engine (`/cohort`)

### `POST /api/v1/cohort/compare`
Executes set-theoretic longitudinal comparison between authoritative snapshots.
- **Request Body:**
  ```json
  {
    "institution_id": "0192e2b3-8fa0-7e11-9a74-d4b8fbc4e891",
    "programme_id": "d04e76d9-81a6-4a41-b8eb-991f82f2c8d2",
    "base_snapshot_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "target_snapshot_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "rule_version_ids": ["c3d9a102-124b-4b11-92b1-6a4a2b91d0e1"]
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "run_id": "e8b0c442-98fc-4c14-9afb-f4c8996fb924",
    "run_code": "RUN-COHORT-2024-2025-APEX-CSE",
    "engine_version": "1.0.0",
    "algorithm_version": "cohort-v2026.1",
    "canonical_serialization_version": "canonical-json-v1",
    "base_headcount": 120,
    "target_headcount": 120,
    "continuing_students_count": 115,
    "documented_transfer_ins_count": 2,
    "documented_transfer_outs_count": 2,
    "unexplained_appearances_count": 3,
    "unexplained_disappearances_count": 3,
    "uncertain_baseline_count": 0,
    "input_provenance_hash": "b2f67...31a",
    "output_provenance_hash": "c89e1...42f",
    "findings_summary": [
      {
        "finding_type": "UNEXPLAINED_APPEARANCE",
        "priority": "HIGH",
        "student_reference": "STU-APEX-2025-089",
        "explanation": "Observed in 2025-26 roster without prior admission episode or documented transfer certificate."
      }
    ]
  }
  ```

---

## 5. Statutory Admission Intake Reconciliation (`/admission`)

### `POST /api/v1/admission/reconcile`
- **Request Body:**
  ```json
  {
    "institution_id": "0192e2b3-8fa0-7e11-9a74-d4b8fbc4e891",
    "programme_id": "d04e76d9-81a6-4a41-b8eb-991f82f2c8d2",
    "academic_year": "2024-25"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "approved_intake": 120,
    "actual_regular_admissions": 120,
    "supernumerary_admissions": 12,
    "supernumerary_quota_cap": 18,
    "lateral_entry_admissions": 10,
    "intake_variance": 0,
    "compliance_status": "COMPLIANT",
    "rule_applied": "RULE_INTAKE_CAP_v2024",
    "findings": []
  }
  ```

---

## 6. Public Verification & Opaque Tokens (`/verification`)

### `POST /api/v1/verification/tokens`
Generates an opaque, cryptographically random verification token for certificates.
- **Request Body:**
  ```json
  {
    "student_identity_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "institution_id": "0192e2b3-8fa0-7e11-9a74-d4b8fbc4e891",
    "programme_id": "d04e76d9-81a6-4a41-b8eb-991f82f2c8d2",
    "certificate_reference": "CERT-APEX-CSE-2026-0042",
    "purpose": "DEGREE_VERIFICATION",
    "validity_days": 365
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "token": "tok_sec_9a8df72c4e1b092a7f5c3d2e1b4a6f8c",
    "qr_url": "https://apaarsetu.aicte.gov.in/verify/tok_sec_9a8df72c4e1b092a7f5c3d2e1b4a6f8c",
    "expires_at": "2027-10-30T10:00:00Z"
  }
  ```

### `GET /api/v1/verification/public-check/{token}`
Public endpoint for QR code scanners. Rate-limited to 10 req/min. Enforces minimal disclosure.
- **Response `200 OK`:**
  ```json
  {
    "valid": true,
    "student_name_masked": "A***** V****",
    "institution_name": "Apex Institute of Technology",
    "programme_name": "Computer Science and Engineering",
    "qualification_level": "UG (B.Tech)",
    "enrolment_status": "GRADUATED",
    "certificate_reference": "CERT-APEX-CSE-2026-0042",
    "issued_academic_year": "2025-26",
    "verification_timestamp": "2026-10-30T10:35:12Z"
  }
  ```

### `POST /api/v1/verification/revoke-token/{token}`
Allows institution or regulatory authority to invalidate a compromised or fraudulent token.
- **Request Body:**
  ```json
  { "revocation_reason": "Student administrative withdrawal confirmed." }
  ```
- **Response `200 OK`:**
  ```json
  { "revoked": true, "token": "tok_sec_...", "revoked_at": "2026-10-30T10:40:00Z" }
  ```

---

## 7. Discrepancies & Reviews (`/discrepancies`, `/reviews`)

### `GET /api/v1/discrepancies`
- **Query Params:** `status`, `priority`, `finding_type`, `page`, `limit`
- **Response `200 OK`:** Paginated list of `review_cases`.

### `POST /api/v1/reviews/{case_id}/decisions`
Submits a reviewer determination with audit trail recording.
- **Request Body:**
  ```json
  {
    "decision": "MARK_LEGITIMATE_TRANSFER",
    "reason": "Institution provided valid Transfer Certificate TC-2025-884 from Kaveri University.",
    "supporting_evidence": {
      "document_hash": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "document_type": "TRANSFER_CERTIFICATE"
    },
    "new_status": "RESOLVED"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "case_id": "case_98f1...",
    "decision_id": "dec_01b2...",
    "new_status": "RESOLVED",
    "audit_event_id": "aud_77e4...",
    "recorded_at": "2026-10-30T10:45:00Z"
  }
  ```

