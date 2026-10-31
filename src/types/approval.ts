export type AllocationType =
  | 'WITHIN_SANCTIONED_INTAKE'
  | 'ADDITIONAL_SUPERNUMERARY'
  | 'INDEPENDENT_CAP'
  | 'INFORMATIONAL_ONLY';

export type AllocationBasis = 'PERCENTAGE' | 'FIXED_SEATS';

export type RoundingMethod =
  | 'FLOOR'
  | 'CEILING'
  | 'ROUND_HALF_UP'
  | 'EXPLICIT_FIXED_CAP';

export type ComplianceStatus =
  | 'COMPLIANT'
  | 'EXCEPTION_FOUND'
  | 'INSUFFICIENT_INFORMATION'
  | 'PARTIALLY_EVALUATED';

export interface ApprovalCategoryAllocation {
  id?: string;
  category_code: string;
  entry_level: string;
  allocation_type: AllocationType;
  allocation_basis: AllocationBasis;
  allocated_value: number;
  rounding_method: RoundingMethod;
  denominator_basis?: string;
  calculated_seat_cap?: number | null;
  policy_clause?: string | null;
}

export interface ApprovalConfiguration {
  id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  approved_intake: number;
  supernumerary_quota_percentage: number;
  lateral_entry_quota_percentage: number;
  approval_reference: string;
  issuing_authority: string;
  approval_letter_date?: string | null;
  effective_from: string;
  effective_to: string;
  configuration_version: number;
  status: 'ACTIVE' | 'SUPERSEDED' | 'REVOKED';
  amendment_reason?: string | null;
  superseded_by_id?: string | null;
  superseded_at?: string | null;
  created_by_user_id: string;
  amended_by_user_id?: string | null;
  created_at: string;
  category_allocations: ApprovalCategoryAllocation[];
}

export interface CategoryComplianceResult {
  category_code: string;
  entry_level: string;
  allocation_type: string;
  approved_limit?: number | null;
  observed_count: number;
  variance?: number | null;
  status: string;
  notes?: string | null;
}

export interface IntakeReconciliationSummary {
  id: string;
  reconciliation_run_id: string;
  approval_configuration_id?: string | null;
  approval_configuration_version?: number | null;
  compliance_status: ComplianceStatus;
  regular_approved_intake: number;
  regular_enrolled_count: number;
  regular_variance: number;
  supernumerary_total_cap: number;
  supernumerary_enrolled_count: number;
  supernumerary_variance: number;
  lateral_entry_approved_cap?: number | null;
  lateral_entry_enrolled_count: number;
  lateral_entry_variance?: number | null;
  unclassified_count: number;
  category_breakdown: CategoryComplianceResult[];
  category_breakdown_json: any;
  discrepancy_cases_created: Array<{
    case_id: string;
    case_number: string;
    classification: string;
    review_priority: string;
    scope_type: string;
  }>;
  created_at: string;
}

