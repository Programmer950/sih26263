import api from './api';

export interface ProgrammeEnrolmentMetric {
  programme_id: string;
  programme_name: string;
  enrolled_count: number;
  approved_intake?: number;
  variance?: number;
}

export interface AcademicYearEnrolmentMetric {
  academic_year: string;
  enrolled_count: number;
}

export interface DashboardSummaryResponse {
  institution_id?: string;
  institution_name?: string;
  role_scope: 'INSTITUTION' | 'SYSTEM_WIDE';
  total_registered_students: number;
  total_institutions: number;
  total_programmes: number;
  total_submissions: number;
  total_snapshots: number;
  total_discrepancy_cases: number;
  open_discrepancies_count: number;
  resolved_discrepancies_count: number;
  apaar_coverage_percentage: number;
  intake_compliance_rate: number;
  enrolment_by_programme: ProgrammeEnrolmentMetric[];
  enrolment_by_academic_year: AcademicYearEnrolmentMetric[];
  recent_activity: Array<{
    id: string;
    action: string;
    entity_type: string;
    timestamp?: string;
    event_hash_preview?: string;
  }>;
}

export const fetchDashboardSummary = async (
  institutionId?: string
): Promise<DashboardSummaryResponse> => {
  const params: Record<string, string> = {};
  if (institutionId) params.institution_id = institutionId;
  const res = await api.get<DashboardSummaryResponse>('/dashboard/summary', { params });
  return res.data;
};

export const downloadReportBlob = async (
  reportType: string,
  institutionId?: string,
  academicYear?: string
): Promise<void> => {
  const params: Record<string, string> = { report_type: reportType };
  if (institutionId) params.institution_id = institutionId;
  if (academicYear) params.academic_year = academicYear;

  const response = await api.get('/dashboard/reports/export', {
    params,
    responseType: 'blob',
  });

  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const filename = `${reportType.toLowerCase().replace(/_/g, '-')}_${new Date().toISOString().slice(0, 10)}.csv`;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const exportCertifiedReport = (reportType: string, institutionId?: string) => {
  downloadReportBlob(reportType, institutionId);
};
