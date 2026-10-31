import React, { useState, useEffect } from 'react';
import {
  fetchCrossInstitutionDuplicates,
  DuplicateConflictItem,
} from '../services/reconciliation';
import { extractErrorMessage } from '../services/api';

export const DuplicateDetection: React.FC = () => {
  const [academicYear, setAcademicYear] = useState<string>('2024-25');
  const [conflicts, setConflicts] = useState<DuplicateConflictItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');

  useEffect(() => {
    loadDuplicates();
  }, [academicYear]);

  const loadDuplicates = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchCrossInstitutionDuplicates(academicYear || undefined);
      setConflicts(data);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('403_FORBIDDEN');
      } else {
        setError(extractErrorMessage(err, 'Failed to query duplicate candidates.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const filteredConflicts = conflicts.filter((c) => {
    if (filterType === 'ALL') return true;
    return c.conflict_type === filterType;
  });

  const concurrentCount = conflicts.filter((c) => c.conflict_type === 'CONCURRENT_DUAL_ENROLMENT').length;
  const transferCount = conflicts.filter((c) => c.conflict_type === 'LEGITIMATE_TRANSFER').length;
  const unresolvedTransferCount = conflicts.filter((c) => c.conflict_type === 'UNRESOLVED_TRANSFER').length;
  const ambiguousCount = conflicts.filter(
    (c) => c.conflict_type === 'AMBIGUOUS_IDENTITY' || c.conflict_type === 'INSUFFICIENT_EVIDENCE'
  ).length;

  if (error === '403_FORBIDDEN') {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded p-6 text-center">
          <div className="w-12 h-12 bg-red-100 text-red-700 rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-xl">
            ✕
          </div>
          <h2 className="text-base font-bold text-red-950 uppercase tracking-wide mb-2">Access Restricted / प्राधिकृत नहीं</h2>
          <p className="text-xs text-red-800">
            Cross-institution duplicate detection requires regulatory or institutional administrative credentials.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#D7DEE5] gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                Cross-Institutional Identity Intelligence
              </span>
              <span className="text-[11px] text-[#5F6B76] font-mono">Blind-Index v1 (HMAC-SHA256)</span>
            </div>
            <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
              Cross-Institution Duplicate Detection / अंतर-संस्थान दोहरी प्रविष्टि संज्ञान
            </h1>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Scans concurrent active student rosters using cryptographic blind indexes. Identifies overlapping enrollments while respecting verified transfers.
            </p>
          </div>

          {/* Academic Year Selector */}
          <div className="flex items-center gap-3">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">Academic Year</label>
              <select
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="gov-input text-xs"
              >
                <option value="2024-25">2024-25 (Current)</option>
                <option value="2023-24">2023-24 (Prior)</option>
                <option value="2022-23">2022-23 (Historical)</option>
              </select>
            </div>
            <div className="pt-4">
              <button
                onClick={loadDuplicates}
                disabled={isLoading}
                className="gov-btn-primary text-xs py-2 px-4"
              >
                {isLoading ? 'Scanning...' : 'Refresh Scan'}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs flex items-center justify-between">
            <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
            <button onClick={() => setError(null)} className="text-red-700 font-bold ml-2">
              ✕
            </button>
          </div>
        )}
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#C0392B] shadow-sm">
          <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Concurrent Dual Enrolments</span>
          <p className="text-2xl font-bold text-[#C0392B] mt-1 font-mono">{concurrentCount}</p>
          <span className="text-[10px] text-[#C0392B] font-semibold">Immediate Investigation Required</span>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#23834A] shadow-sm">
          <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Legitimate Transfers</span>
          <p className="text-2xl font-bold text-[#12345A] mt-1 font-mono">{transferCount}</p>
          <span className="text-[10px] text-[#23834A] font-semibold">Verified Transfer Evidence</span>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#E58A24] shadow-sm">
          <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Unresolved Transfers</span>
          <p className="text-2xl font-bold text-[#E58A24] mt-1 font-mono">{unresolvedTransferCount}</p>
          <span className="text-[10px] text-[#E58A24] font-semibold">Pending Documentation Verification</span>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#8F6B00] shadow-sm">
          <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Ambiguous / Insufficient</span>
          <p className="text-2xl font-bold text-[#12345A] mt-1 font-mono">{ambiguousCount}</p>
          <span className="text-[10px] text-[#8F6B00] font-semibold">Missing Admission/Exit Dates</span>
        </div>
      </div>

      {/* Conflict Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 bg-white border border-[#D7DEE5] rounded p-3">
        {[
          { label: `All Candidates (${conflicts.length})`, value: 'ALL' },
          { label: `Concurrent Dual (${concurrentCount})`, value: 'CONCURRENT_DUAL_ENROLMENT' },
          { label: `Verified Transfers (${transferCount})`, value: 'LEGITIMATE_TRANSFER' },
          { label: `Unresolved Transfers (${unresolvedTransferCount})`, value: 'UNRESOLVED_TRANSFER' },
          { label: `Insufficient Evidence (${ambiguousCount})`, value: 'INSUFFICIENT_EVIDENCE' },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilterType(tab.value)}
            className={`px-2.5 py-1 rounded text-xs font-medium transition ${
              filterType === tab.value
                ? 'bg-[#12345A] text-white shadow-xs'
                : 'bg-[#F4F6F8] hover:bg-[#EAF2F8] text-[#202B36] border border-[#D7DEE5]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Conflicts List */}
      {isLoading ? (
        <div className="py-12 text-center text-[#5F6B76] text-xs">Scanning active rosters for candidate collisions...</div>
      ) : filteredConflicts.length === 0 ? (
        <div className="bg-white border border-[#D7DEE5] rounded p-12 text-center shadow-sm">
          <div className="w-12 h-12 bg-[#EAF7EE] text-[#23834A] border border-[#23834A] rounded-full flex items-center justify-center mx-auto mb-3 font-bold text-lg">
            ✓
          </div>
          <h3 className="text-base font-bold text-[#12345A] uppercase tracking-wide mb-1">No Candidate Conflicts Detected</h3>
          <p className="text-xs text-[#5F6B76] max-w-md mx-auto">
            No cross-institution duplicate enrollment anomalies were found for academic year {academicYear} under the selected filter.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredConflicts.map((c) => (
            <div key={c.id} className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#D7DEE5]">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-[#EAF2F8] text-[#12345A] border border-[#CBD7E3] flex items-center justify-center font-bold text-xs">
                    {c.full_name.charAt(0)}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-[#12345A]">{c.full_name}</h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs font-mono text-[#174F82] font-semibold">
                        APAAR: {c.masked_apaar_reference || 'MASKED'}
                      </span>
                      <span className="text-[10px] bg-[#F4F6F8] border border-[#D7DEE5] text-[#5F6B76] px-1.5 py-0.2 rounded font-mono">
                        {c.blind_index.substring(0, 14)}...
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`gov-badge ${
                      c.conflict_type === 'CONCURRENT_DUAL_ENROLMENT'
                        ? 'gov-badge-danger'
                        : c.conflict_type === 'LEGITIMATE_TRANSFER'
                        ? 'gov-badge-verified'
                        : c.conflict_type === 'UNRESOLVED_TRANSFER'
                        ? 'gov-badge-warning'
                        : 'gov-badge-neutral'
                    }`}
                  >
                    {c.conflict_type.replace(/_/g, ' ')}
                  </span>
                  <span
                    className={`gov-badge ${
                      c.review_priority === 'HIGH'
                        ? 'gov-badge-danger'
                        : c.review_priority === 'MEDIUM'
                        ? 'gov-badge-warning'
                        : 'gov-badge-neutral'
                    }`}
                  >
                    {c.review_priority}
                  </span>
                </div>
              </div>

              {/* Institution Enrolment Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {c.enrolments.map((e, idx) => (
                  <div key={idx} className="p-3 bg-[#F4F6F8] border border-[#D7DEE5] rounded text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[#12345A]">{e.institution_name}</span>
                      <span className="text-[10px] bg-[#EAF2F8] border border-[#CBD7E3] text-[#12345A] px-1.5 py-0.5 rounded font-mono">
                        {e.academic_year}
                      </span>
                    </div>
                    <div className="text-[#202B36]">{e.programme_name}</div>
                    <div className="flex items-center justify-between text-[11px] text-[#5F6B76] pt-1.5 border-t border-[#D7DEE5]">
                      <span>Admission: <strong>{e.admission_date || 'No Date Recorded'}</strong></span>
                      <span className="capitalize">Seat: <strong>{e.seat_accounting_category || 'REGULAR'}</strong></span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Evidence & Regulatory Findings */}
              <div className="p-3 bg-[#EAF2F8] border border-[#CBD7E3] rounded text-xs text-[#12345A] flex items-start gap-2">
                <span className="font-bold">Provenance & Regulatory Evidence:</span>
                <span>{c.evidence_summary}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
