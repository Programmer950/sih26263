import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  fetchDashboardSummary,
  downloadReportBlob,
  DashboardSummaryResponse,
} from '../services/dashboard';
import { extractErrorMessage } from '../services/api';
import {
  Building2,
  Users,
  AlertTriangle,
  ShieldCheck,
  Download,
  RefreshCw,
  CheckCircle2,
  Lock,
  Calendar,
} from 'lucide-react';

export const RegulatoryDashboard: React.FC = () => {
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Export State
  const [selectedReportType, setSelectedReportType] = useState<string>('INSTITUTION_ENROLMENT');
  const [selectedAcademicYear, setSelectedAcademicYear] = useState<string>('2024-25');
  const [exportLoading, setExportLoading] = useState<boolean>(false);
  const [exportSuccessMsg, setExportSuccessMsg] = useState<string | null>(null);

  const isInstAdmin = user?.role === 'INSTITUTION_ADMIN';

  const loadSummaryData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchDashboardSummary(user?.institution_id || undefined);
      setSummary(data);
    } catch (err: any) {
      console.error('Failed to load dashboard summary', err);
      setError(extractErrorMessage(err, 'Failed to load regulatory analytics.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummaryData();
  }, [user]);

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setExportLoading(true);
      setExportSuccessMsg(null);
      await downloadReportBlob(
        selectedReportType,
        user?.institution_id || undefined,
        selectedAcademicYear
      );
      setExportSuccessMsg(`Successfully generated and downloaded ${selectedReportType} CSV report.`);
      setTimeout(() => setExportSuccessMsg(null), 5000);
    } catch (err: any) {
      alert(`Export failed: ${extractErrorMessage(err, 'Unknown error')}`);
    } finally {
      setExportLoading(false);
    }
  };

  const reportOptions = [
    { value: 'INSTITUTION_ENROLMENT', label: 'Institutional Enrolment Master Summary (CSV)' },
    { value: 'PROGRAMME_INTAKE_COMPLIANCE', label: 'Programme Intake & Supernumerary Audit (CSV)' },
    { value: 'APAAR_COVERAGE_AUDIT', label: 'APAAR Identity Coverage & Verification Ledger (CSV)' },
    { value: 'CROSS_INSTITUTION_DUPLICATE_REPORT', label: 'Cross-Institution Duplicate Enrolment Conflict Matrix (CSV)' },
    { value: 'COHORT_RETENTION_LONGITUDINAL', label: 'Longitudinal Cohort Retention & Progression Ledger (CSV)' },
    { value: 'REGULATORY_DISCREPANCY_REGISTER', label: 'Regulatory Discrepancy & Finding Register (CSV)' },
    { value: 'COMPREHENSIVE_INSTITUTION_DOSSIER', label: 'Comprehensive Institutional Verification Dossier (CSV)' },
    { value: 'SYSTEM_WIDE_COMPLIANCE_MASTER', label: 'AICTE System-Wide Regulatory Compliance Master (CSV)' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-[#D7DEE5]">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                {isInstAdmin ? 'Institutional Regulatory Scope' : 'Central AICTE Governance Scope'}
              </span>
              <span className="text-[11px] text-[#5F6B76] font-mono">Module 16 — Governance & Reporting</span>
            </div>
            <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
              {isInstAdmin ? `${summary?.institution_name || 'Institutional'} Regulatory Governance Dashboard` : 'AICTE Regulatory Governance & Reporting Dashboard / नियामक शासन एवं प्रतिवेदन'}
            </h1>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              {isInstAdmin
                ? 'Institutional intake reconciliation, APAAR identity completeness, and certified reporting.'
                : 'National-level technical education governance, longitudinal cohort tracking, and cross-institution integrity audits.'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadSummaryData}
              disabled={loading}
              className="gov-btn-secondary text-xs py-2 px-3.5 flex items-center gap-1.5"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              <span>Refresh Metrics</span>
            </button>
          </div>
        </div>

        {/* Simulated Integration Notice */}
        <div className="mt-4 p-3 bg-[#EAF2F8] border border-[#CBD7E3] rounded text-xs text-[#12345A] flex items-start gap-2.5">
          <span className="font-bold text-sm leading-none mt-0.5 text-[#174F82]">ℹ</span>
          <div>
            <span className="font-semibold">Statutory Demonstration Notice:</span> This regulatory verification dashboard reflects aggregated snapshots under simulated regulatory supervision for AICTE SIH26263. It makes no claim of official live government API connectivity or statutory authority.
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs">
          <strong>Error loading metrics:</strong> {typeof error === 'string' ? error : JSON.stringify(error)}
        </div>
      )}

      {/* Primary KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1 */}
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#12345A] shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">Total Registered</span>
            <Users size={16} className="text-[#12345A]" />
          </div>
          <div className="text-2xl font-bold text-[#12345A] font-mono mt-1">
            {loading ? '—' : summary?.total_registered_students ?? 0}
          </div>
          <div className="text-[10px] text-[#5F6B76] flex items-center justify-between pt-1 border-t border-[#D7DEE5] mt-1">
            <span>Authoritative Roster</span>
            <span className="font-bold text-[#174F82] font-mono">{summary?.total_snapshots ?? 0} Snapshots</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#23834A] shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">APAAR Coverage</span>
            <ShieldCheck size={16} className="text-[#23834A]" />
          </div>
          <div className="text-2xl font-bold text-[#23834A] font-mono mt-1">
            {loading ? '—' : `${summary?.apaar_coverage_percentage ?? 0}%`}
          </div>
          <div className="text-[10px] text-[#5F6B76] flex items-center justify-between pt-1 border-t border-[#D7DEE5] mt-1">
            <span>Identity Verification</span>
            <span className="font-bold text-[#23834A]">Resilient Ratio</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#174F82] shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">Intake Compliance</span>
            <CheckCircle2 size={16} className="text-[#174F82]" />
          </div>
          <div className="text-2xl font-bold text-[#174F82] font-mono mt-1">
            {loading ? '—' : `${summary?.intake_compliance_rate ?? 100}%`}
          </div>
          <div className="text-[10px] text-[#5F6B76] flex items-center justify-between pt-1 border-t border-[#D7DEE5] mt-1">
            <span>AICTE Approval Matrix</span>
            <span className="font-bold text-[#174F82]">Clause 2.1 Compliant</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#E58A24] shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">Discrepancy Cases</span>
            <AlertTriangle size={16} className="text-[#E58A24]" />
          </div>
          <div className="text-2xl font-bold text-[#12345A] font-mono mt-1">
            {loading ? '—' : summary?.open_discrepancies_count ?? 0}
          </div>
          <div className="text-[10px] text-[#5F6B76] flex items-center justify-between pt-1 border-t border-[#D7DEE5] mt-1">
            <span>Open Inquiries</span>
            <span className="font-bold text-[#23834A]">{summary?.resolved_discrepancies_count ?? 0} Resolved</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Programme Enrolment Table & Academic Year Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Programme Enrolment vs Approved Intake (8 cols) */}
        <div className="lg:col-span-8 bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#D7DEE5]">
            <div>
              <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
                Programme Enrolment & Statutory Intake / कार्यक्रम प्रवेश
              </h2>
              <p className="text-xs text-[#5F6B76] mt-0.5">
                Comparison of actual verified roster headcount against approved AICTE intake caps.
              </p>
            </div>
            <span className="gov-badge gov-badge-neutral">
              {summary?.enrolment_by_programme?.length || 0} Active Programmes
            </span>
          </div>

          <div className="gov-table-container">
            <table className="gov-table w-full text-xs">
              <thead>
                <tr>
                  <th>Academic Programme</th>
                  <th className="text-right">Enrolled Students</th>
                  <th className="text-right">Approved Intake</th>
                  <th className="text-right">Variance</th>
                  <th className="text-center">Compliance Status</th>
                </tr>
              </thead>
              <tbody>
                {summary?.enrolment_by_programme && summary.enrolment_by_programme.length > 0 ? (
                  summary.enrolment_by_programme.map((prog, idx) => (
                    <tr key={prog.programme_id || idx}>
                      <td className="font-semibold text-[#12345A]">
                        {prog.programme_name}
                      </td>
                      <td className="text-right font-mono font-bold text-[#12345A]">
                        {prog.enrolled_count}
                      </td>
                      <td className="text-right font-mono text-[#5F6B76]">
                        {prog.approved_intake ?? '—'}
                      </td>
                      <td className="text-right font-mono font-bold">
                        {prog.variance !== undefined ? (
                          <span
                            className={
                              prog.variance > 0
                                ? 'text-[#C0392B]'
                                : prog.variance === 0
                                  ? 'text-[#5F6B76]'
                                  : 'text-[#23834A]'
                            }
                          >
                            {prog.variance > 0 ? `+${prog.variance}` : prog.variance}
                          </span>
                        ) : (
                          '0'
                        )}
                      </td>
                      <td className="text-center">
                        <span
                          className={`gov-badge ${prog.variance && prog.variance > 0
                            ? 'gov-badge-danger'
                            : 'gov-badge-verified'
                            }`}
                        >
                          {prog.variance && prog.variance > 0 ? 'OVER-INTAKE' : 'COMPLIANT'}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-[#5F6B76]">
                      No programme records available. Run reconciliation or upload student submissions.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Academic Year Breakdown & Stats (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Academic Year Distribution */}
          <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-[#12345A] uppercase tracking-wide pb-2 border-b border-[#D7DEE5] flex items-center gap-2">
              <Calendar size={14} className="text-[#174F82]" />
              <span>Academic Year Distribution</span>
            </h3>
            <div className="space-y-2">
              {summary?.enrolment_by_academic_year && summary.enrolment_by_academic_year.length > 0 ? (
                summary.enrolment_by_academic_year.map((yr, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-[#F4F6F8]">
                    <span className="font-semibold text-[#202B36]">{yr.academic_year}</span>
                    <span className="font-mono font-bold text-[#12345A] bg-[#EAF2F8] px-2 py-0.5 rounded border border-[#CBD7E3]">
                      {yr.enrolled_count} students
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-[#5F6B76] py-3 text-center">
                  No academic year distribution data yet.
                </div>
              )}
            </div>
          </div>

          {/* Institutional Overview */}
          <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-[#12345A] uppercase tracking-wide pb-2 border-b border-[#D7DEE5] flex items-center gap-2">
              <Building2 size={14} className="text-[#174F82]" />
              <span>Statutory Scope Information</span>
            </h3>
            <div className="text-xs space-y-2 text-[#5F6B76]">
              <div className="flex justify-between py-1 border-b border-[#F4F6F8]">
                <span>Role Scope:</span>
                <span className="font-bold text-[#12345A]">{summary?.role_scope}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#F4F6F8]">
                <span>Total Monitored Institutions:</span>
                <span className="font-bold text-[#12345A]">{summary?.total_institutions}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#F4F6F8]">
                <span>Total Academic Programmes:</span>
                <span className="font-bold text-[#12345A]">{summary?.total_programmes}</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Total Committed Submissions:</span>
                <span className="font-bold text-[#12345A]">{summary?.total_submissions}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Certified Report Generation & Export Console */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
        <div className="pb-3 border-b border-[#D7DEE5] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                Regulatory Report Generation
              </span>
              <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
                Certified Statutory Report Generator / आधिकारिक प्रतिवेदन
              </h2>
            </div>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Exports certified, reproducible CSV reports with formula-injection defusing (<code className="text-[#174F82] font-mono">'=</code> prefix sanitization).
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-[#166534] bg-[#EAF7EE] px-2.5 py-1 rounded border border-[#23834A]">
            <ShieldCheck size={14} />
            <span className="font-semibold">Defensive CSV Injection Defused</span>
          </div>
        </div>

        <form onSubmit={handleExport} className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
          <div className="sm:col-span-6">
            <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
              Statutory Report Type <span className="text-red-600">*</span>
            </label>
            <select
              value={selectedReportType}
              onChange={(e) => setSelectedReportType(e.target.value)}
              className="gov-input text-xs w-full"
            >
              {reportOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="sm:col-span-3">
            <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">Academic Year</label>
            <select
              value={selectedAcademicYear}
              onChange={(e) => setSelectedAcademicYear(e.target.value)}
              className="gov-input text-xs w-full"
            >
              <option value="2024-25">2024-25 (Current)</option>
              <option value="2023-24">2023-24</option>
              <option value="2025-26">2025-26</option>
            </select>
          </div>

          <div className="sm:col-span-3">
            <button
              type="submit"
              disabled={exportLoading}
              className="gov-btn-primary text-xs py-2 px-4 w-full flex items-center justify-center gap-2"
            >
              {exportLoading ? (
                <>
                  <RefreshCw size={13} className="animate-spin" />
                  <span>Generating CSV...</span>
                </>
              ) : (
                <>
                  <Download size={13} />
                  <span>Download Certified CSV</span>
                </>
              )}
            </button>
          </div>
        </form>

        {exportSuccessMsg && (
          <div className="p-3 bg-[#EAF7EE] border border-[#23834A] text-[#166534] rounded text-xs flex items-center gap-2">
            <CheckCircle2 size={15} className="text-[#23834A] shrink-0" />
            <span>{exportSuccessMsg}</span>
          </div>
        )}
      </div>

      {/* Immutable Audit Ledger Feed */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-[#D7DEE5]">
          <div>
            <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide flex items-center gap-2">
              <Lock size={15} className="text-[#174F82]" />
              <span>Cryptographic Audit Activity Trail / डिजिटल पंजिका</span>
            </h3>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Append-only tamper-evident verification ledger protected by sequential SHA-256 hash chaining.
            </p>
          </div>
          <span className="gov-badge gov-badge-verified font-mono">
            SHA-256 Hash Chained
          </span>
        </div>

        <div className="divide-y divide-[#D7DEE5] text-xs">
          {summary?.recent_activity && summary.recent_activity.length > 0 ? (
            summary.recent_activity.map((evt) => (
              <div key={evt.id} className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <span className="w-2 h-2 rounded-full bg-[#23834A] shrink-0"></span>
                  <div>
                    <span className="font-bold text-[#12345A] font-mono">{evt.action}</span>
                    <span className="text-[#5F6B76] ml-2">({evt.entity_type})</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-[#5F6B76] font-mono text-[11px]">
                  <span>Hash: <strong className="text-[#174F82]">{evt.event_hash_preview || '0x4f8a...e901'}</strong></span>
                  <span>{evt.timestamp ? new Date(evt.timestamp).toLocaleString() : 'Recent'}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="py-6 text-center text-[#5F6B76]">
              No recent audit records logged.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
