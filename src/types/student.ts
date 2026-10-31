export interface StudentSummary {
  id: string; // student_identity_id
  internal_student_uuid: string;
  full_name: string;
  masked_apaar_reference?: string | null;
  identity_status: 'FORMAT_VALID' | 'MISSING_APAAR' | 'INVALID_FORMAT' | 'EXTERNALLY_VERIFIED' | 'DISPUTED';
  institution_id: string;
  institution_name: string;
  institution_student_id: string;
  programme_id: string;
  programme_code: string;
  programme_name: string;
  status: string;
  latest_academic_year: string;
}

export interface StudentTimelineEvent {
  type: 'ADMISSION' | 'ANNUAL_OBSERVATION' | 'TRANSFER';
  date?: string;
  timestamp?: string;
  academic_year: string;
  institution?: string;
  programme?: string;
  category?: string;
  supernumerary?: boolean;
  status?: string;
  description: string;
}

export interface StudentTimeline {
  identity: {
    id: string;
    internal_student_uuid: string;
    full_name: string;
    masked_apaar: string;
    identity_status: string;
    date_of_birth?: string | null;
    gender?: string | null;
  };
  institutions_enrolled: Array<{
    institution_name: string;
    institution_code: string;
    programme_name: string;
    student_id: string;
    status: string;
  }>;
  timeline: StudentTimelineEvent[];
}

