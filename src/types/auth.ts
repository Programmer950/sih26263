export type UserRole = 'SYSTEM_ADMIN' | 'REGULATORY_REVIEWER' | 'INSTITUTION_ADMIN' | 'STUDENT_VERIFIER';

export interface UserSummary {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  institution_id?: string | null;
  institution_name?: string | null;
  institution_code?: string | null;
}

export interface UserProfile extends UserSummary {
  permissions: Record<string, any>;
  last_login_at?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserSummary;
}

export interface InstitutionSummary {
  id: string;
  institution_code: string;
  name: string;
  category: string;
  approval_status: string;
  state: string;
  district: string;
  pincode?: string;
  address?: string;
  contact_email?: string;
  programme_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProgrammeSummary {
  id: string;
  institution_id: string;
  programme_code: string;
  programme_name: string;
  qualification_level: string;
  duration_years: number;
  status: string;
  approved_intake?: number | null;
  academic_year?: string | null;
}

