import api from './api';

export interface EnrolmentInstitutionContext {
  institution_id: string;
  institution_name: string;
  programme_id: string;
  programme_name: string;
  academic_year: string;
  snapshot_id?: string;
  submission_id?: string;
  admission_date?: string;
  exit_date?: string;
  entry_level?: string;
  seat_accounting_category?: string;
  student_status?: string;
}

export interface DuplicateConflictItem {
  id: string;
  student_identity_id: string;
  masked_apaar_reference?: string;
  full_name: string;
  blind_index: string;
  blind_index_version: string;
  identity_verification_status: string;
  academic_year: string;
  conflict_type: 'CONCURRENT_DUAL_ENROLMENT' | 'LEGITIMATE_TRANSFER' | 'UNRESOLVED_TRANSFER' | 'INSUFFICIENT_EVIDENCE' | 'AMBIGUOUS_IDENTITY';
  review_priority: 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  enrolments: EnrolmentInstitutionContext[];
  transfer_event_id?: string;
  is_verified_transfer: boolean;
  discrepancy_case_id?: string;
  evidence_summary: string;
}

export interface UnifiedCohortSummary {
  reconciliation_run_id: string;
  candidate_snapshot_id: string;
  baseline_snapshot_id?: string;
  total_candidate_observations: number;
  continuing_count: number;
  added_count: number;
  documented_transfer_count: number;
  unexplained_appearance_count: number;
  ambiguous_identity_count: number;
  insufficient_evidence_count: number;
  baseline_disappearances: Record<string, number>;
  engine_version: string;
  rules_version: string;
  run_status: string;
}

export interface UnifiedIntakeSummary {
  intake_summary_id?: string;
  approval_configuration_id?: string;
  approval_configuration_version?: number;
  approved_intake: number;
  enrolled_count: number;
  variance: number;
  compliance_status: string;
  category_results: Array<Record<string, any>>;
  engine_version: string;
  rules_version: string;
}

export interface UnifiedReconciliationResponse {
  reconciliation_run_id: string;
  snapshot_id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  status: string;
  cohort_summary: UnifiedCohortSummary;
  intake_summary?: UnifiedIntakeSummary;
  duplicate_candidates: DuplicateConflictItem[];
  discrepancy_cases_created: Array<{
    case_id: string;
    case_number: string;
    scope_type: string;
    classification: string;
    review_priority: string;
    status: string;
  }>;
  executed_at: string;
}

export interface RosterSnapshotItem {
  id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  is_authoritative: boolean;
  lifecycle_status: string;
  declared_headcount: number;
  observed_headcount: number;
  snapshot_hash: string;
  snapshot_metadata?: Record<string, any>;
  created_at: string;
}

export interface ResultItemDetail {
  id: string;
  student_identity_id: string;
  student_name: string;
  masked_apaar?: string;
  classification: string;
  review_priority: string;
  system_explanation: string;
  is_case_eligible: boolean;
  discrepancy_case_id?: string;
  candidate_row_number?: number;
  baseline_row_number?: number;
}

export const fetchCrossInstitutionDuplicates = async (
  academicYear?: string
): Promise<DuplicateConflictItem[]> => {
  const params: Record<string, string> = {};
  if (academicYear) params.academic_year = academicYear;
  const res = await api.get<DuplicateConflictItem[]>('/reconciliation/duplicates', { params });
  return res.data;
};

export const executeUnifiedReconciliation = async (
  snapshotId: string,
  baselineSnapshotId?: string,
  approvalConfigId?: string
): Promise<UnifiedReconciliationResponse> => {
  const payload: Record<string, any> = { snapshot_id: snapshotId };
  if (baselineSnapshotId) payload.baseline_snapshot_id = baselineSnapshotId;
  if (approvalConfigId) payload.approval_config_id = approvalConfigId;
  const res = await api.post<UnifiedReconciliationResponse>('/reconciliation/unified', payload);
  return res.data;
};

export const fetchSnapshotsList = async (institutionId?: string): Promise<RosterSnapshotItem[]> => {
  const params: Record<string, string> = {};
  if (institutionId) params.institution_id = institutionId;
  const res = await api.get<{ items: RosterSnapshotItem[] }>('/snapshots', { params });
  return res.data.items || [];
};

export const fetchRunResultItems = async (runId: string): Promise<ResultItemDetail[]> => {
  try {
    const res = await api.get<{ items: ResultItemDetail[] }>(`/reconciliation/runs/${runId}/items`, {
      params: { limit: 100 },
    });
    return res.data.items || [];
  } catch (err: any) {
    if (err.response?.status === 404) {
      const fallbackRes = await api.get<{ items: ResultItemDetail[] }>(`/reconciliation/runs/${runId}/results`, {
        params: { limit: 100 },
      });
      return fallbackRes.data.items || [];
    }
    throw err;
  }
};

export interface AggregateDeclarationItem {
  id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  declared_count: number;
  population_definition: string;
  student_status_definition: string;
  counting_methodology: string;
  reporting_source: string;
  source_reference: string;
  declaration_date?: string;
  created_at: string;
}

export interface AggregateReconciliationResult {
  reconciliation_run_id?: string;
  declaration_id: string;
  snapshot_id?: string;
  roster_snapshot_id?: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  declared_count: number;
  roster_count: number;
  variance: number;
  comparability_status: 'COMPARABLE' | 'NON_COMPARABLE';
  reconciliation_status?: 'MATCH' | 'DISCREPANT' | 'NON_COMPARABLE' | string;
  outcome_status?: 'EXACT_MATCH' | 'ROSTER_EXCESS' | 'DECLARED_EXCESS' | 'INCOMPARABLE' | string;
  explanation: string;
  discrepancy_case_id?: string;
  run_metadata?: Record<string, any>;
  source_references?: string[];
  reconciliation_timestamp?: string;
}

export const fetchAggregateDeclarations = async (
  institutionId?: string,
  academicYear?: string
): Promise<AggregateDeclarationItem[]> => {
  const params: Record<string, string> = {};
  if (institutionId) params.institution_id = institutionId;
  if (academicYear) params.academic_year = academicYear;
  const res = await api.get<AggregateDeclarationItem[]>('/reconciliation/aggregate/declarations', { params });
  return res.data;
};

export const createAggregateDeclaration = async (
  payload: {
    institution_id: string;
    programme_id: string;
    academic_year: string;
    declared_count: number;
    population_definition: string;
    student_status_definition: string;
    counting_methodology: string;
    reporting_source: string;
    source_reference: string;
    declaration_date?: string;
    declaration_metadata?: Record<string, any>;
  }
): Promise<AggregateDeclarationItem> => {
  const res = await api.post<AggregateDeclarationItem>('/reconciliation/aggregate/declarations', payload);
  return res.data;
};

export const reconcileAggregateWithRoster = async (
  payload: {
    declaration_id: string;
    snapshot_id?: string;
    roster_snapshot_id?: string;
    generate_discrepancy_on_variance?: boolean;
  }
): Promise<AggregateReconciliationResult> => {
  const snapshotId = payload.roster_snapshot_id || payload.snapshot_id;
  const res = await api.post<AggregateReconciliationResult>('/reconciliation/aggregate/reconcile', {
    declaration_id: payload.declaration_id,
    roster_snapshot_id: snapshotId,
    snapshot_id: snapshotId,
    generate_discrepancy_on_variance: payload.generate_discrepancy_on_variance,
  });
  return res.data;
};

