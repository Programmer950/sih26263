import api from './api';

export interface UploadResponse {
  submission_id: string;
  submission_status: string;
  file_fingerprint: string;
  original_filename: string;
  file_size_bytes: number;
  detected_encoding?: string;
  total_rows_count: number;
  valid_rows_count: number;
  warning_rows_count: number;
  error_rows_count: number;
  duplicate_rows_count: number;
  detected_headers: string[];
  suggested_mapping: Record<string, string | null>;
  sample_rows: any[];
}

export interface PreviewResponse {
  preview_id: string;
  submission_id: string;
  file_fingerprint: string;
  mapping_version: string;
  mapping_hash: string;
  detected_encoding?: string;
  total_rows_count: number;
  valid_rows_count: number;
  warning_rows_count: number;
  error_rows_count: number;
  duplicate_rows_count: number;
  column_mapping: Record<string, string>;
  validation_summary: Record<string, any>;
  sample_rows?: any[];
  created_at: string;
}

export interface ConfirmResponse {
  submission_id: string;
  submission_status: string;
  snapshot_id?: string;
  total_records_processed: number;
  valid_records: number;
  warning_records: number;
  error_records: number;
  snapshot_status?: string;
  completeness_status?: string;
  is_authoritative: boolean;
  committed_at: string;
}

export interface SubmissionSummary {
  id: string;
  institution_id: string;
  programme_id: string;
  academic_year: string;
  submission_type: string;
  original_filename: string;
  file_fingerprint: string;
  file_size_bytes: number;
  submission_status: string;
  total_rows_count?: number;
  valid_rows_count?: number;
  warning_rows_count?: number;
  error_rows_count?: number;
  duplicate_rows_count?: number;
  created_at: string;
  committed_at?: string;
}

export interface PaginatedSubmissionsResponse {
  items: SubmissionSummary[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export async function uploadSubmissionFile(formData: FormData): Promise<UploadResponse> {
  const res = await api.post<UploadResponse>('/submissions/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
}

export async function generateSubmissionPreview(
  submissionId: string,
  columnMapping: Record<string, string>
): Promise<PreviewResponse> {
  const res = await api.post<PreviewResponse>(`/submissions/${submissionId}/preview`, {
    column_mapping: columnMapping,
  });
  return res.data;
}

export async function confirmSubmissionIngestion(
  submissionId: string,
  payload: {
    preview_id: string;
    column_mapping: Record<string, string>;
    completeness_status?: string;
    mark_as_authoritative?: boolean;
  }
): Promise<ConfirmResponse> {
  const res = await api.post<ConfirmResponse>(`/submissions/${submissionId}/confirm`, payload);
  return res.data;
}

export async function listSubmissions(params?: {
  page?: number;
  limit?: number;
  institution_id?: string;
  programme_id?: string;
}): Promise<PaginatedSubmissionsResponse> {
  const res = await api.get<PaginatedSubmissionsResponse>('/submissions', { params });
  return res.data;
}

export async function cancelSubmission(submissionId: string): Promise<any> {
  const res = await api.post(`/submissions/${submissionId}/cancel`);
  return res.data;
}
