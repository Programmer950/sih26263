export type DiscrepancyClassification =
  | 'ADDED'
  | 'CONTINUING'
  | 'WITHDRAWN'
  | 'DOCUMENTED_TRANSFER'
  | 'UNEXPLAINED_APPEARANCE'
  | 'UNEXPLAINED_DISAPPEARANCE'
  | 'AMBIGUOUS_IDENTITY'
  | 'INSUFFICIENT_EVIDENCE';

export type ReviewPriority = 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';

export type CaseStatus =
  | 'OPEN'
  | 'UNDER_INVESTIGATION'
  | 'INVESTIGATING'
  | 'EVIDENCE_REQUESTED'
  | 'EXPLANATION_SUBMITTED'
  | 'CORRECTION_SUBMITTED'
  | 'CORRECTION_RECORDED'
  | 'VERIFIED_VALID'
  | 'CLOSED';

export type DecisionAction =
  | 'START_INVESTIGATION'
  | 'REQUEST_EVIDENCE'
  | 'SUBMIT_EXPLANATION'
  | 'CONFIRM_VALID'
  | 'RECORD_CORRECTION'
  | 'CLOSE_CASE'
  | 'REOPEN_CASE';

export interface DiscrepancyDecision {
  id: string;
  discrepancy_case_id: string;
  action: DecisionAction;
  prior_status: CaseStatus;
  new_status: CaseStatus;
  decision_reason: string;
  supporting_evidence_ref: string | null;
  recorded_by_user_id: string;
  recorded_by_email?: string;
  created_at: string;
}

export interface DiscrepancyCase {
  id: string;
  case_number: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  student_identity_id: string;
  student_name: string;
  masked_apaar: string;
  classification: DiscrepancyClassification;
  priority: ReviewPriority;
  case_status: CaseStatus;
  occurrence_count: number;
  first_observed_at: string;
  latest_observed_at: string;
  initial_reconciliation_run_id: string;
  latest_reconciliation_run_id: string;
  linked_prior_case_id: string | null;
  system_notes: string | null;
  decisions?: DiscrepancyDecision[];
  created_at: string;
  updated_at: string;
}

export interface ReconciliationResultItem {
  id: string;
  reconciliation_run_id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  student_identity_id: string;
  student_name: string;
  masked_apaar: string;
  classification: DiscrepancyClassification;
  review_priority: ReviewPriority;
  is_case_eligible: boolean;
  discrepancy_case_id: string | null;
  candidate_observation_id: string | null;
  candidate_submission_id: string | null;
  candidate_row_number: number | null;
  baseline_observation_id: string | null;
  baseline_submission_id: string | null;
  baseline_row_number: number | null;
  system_explanation: string;
  created_at: string;
}

export interface ReconciliationRun {
  id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  candidate_snapshot_id: string;
  candidate_snapshot_hash: string;
  baseline_snapshot_id: string | null;
  baseline_snapshot_hash: string | null;
  run_type: string;
  execution_status: string;
  engine_version: string;
  rules_version: string;
  result_fingerprint: string;
  summary_counts: Record<string, number>;
  initiated_by_user_id: string;
  created_at: string;
}

