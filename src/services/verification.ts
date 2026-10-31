import api from './api';

export interface VerificationRequestPayload {
  apaar_id: string;
  stated_purpose: string;
  consent_confirmed: boolean;
  organization_name?: string;
  verifier_name?: string;
}

export interface DisclosedStudentRecord {
  student_name: string;
  masked_apaar: string;
  institution_name: string;
  programme_name: string;
  academic_year: string;
  enrolment_status: string;
  supported_status: string;
}

export interface VerificationRequestResponse {
  verification_reference: string;
  status: 'VERIFIED' | 'NOT_FOUND' | 'UNAVAILABLE' | 'EXPIRED' | 'REVOKED';
  token?: string;
  qr_payload?: string;
  disclosed_record?: DisclosedStudentRecord;
  message?: string;
  expires_at?: string;
}

export interface QRVerificationResponse {
  valid: boolean;
  status: 'VERIFIED' | 'INVALID' | 'EXPIRED' | 'REVOKED';
  reason?: string;
  verification_reference?: string;
  disclosed_record?: DisclosedStudentRecord;
  verified_at?: string;
}

export const requestStudentVerification = async (
  payload: VerificationRequestPayload
): Promise<VerificationRequestResponse> => {
  const res = await api.post<VerificationRequestResponse>('/verification/request', payload);
  return res.data;
};

export const verifyQrToken = async (token: string): Promise<QRVerificationResponse> => {
  if (!token || !token.trim()) {
    return {
      valid: false,
      status: 'INVALID',
      reason: 'Verification token is missing or empty.',
    };
  }
  const res = await api.get<QRVerificationResponse>(`/verification/qr/${encodeURIComponent(token.trim())}`);
  return res.data;
};

