import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  fetchSnapshotsList,
  executeUnifiedReconciliation,
  fetchRunResultItems,
  RosterSnapshotItem,
  UnifiedReconciliationResponse,
  ResultItemDetail,
} from '../services/reconciliation';
import { extractErrorMessage } from '../services/api';

export const CohortExplorer: React.FC = () => {
  const { user } = useAuth();
  const [snapshots, setSnapshots] = useState<RosterSnapshotItem[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>('');
  const [selectedBaselineId, setSelectedBaselineId] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [unifiedResult, setUnifiedResult] = useState<UnifiedReconciliationResponse | null>(null);
  const [studentItems, setStudentItems] = useState<ResultItemDetail[]>([]);
  const [filterClassification, setFilterClassification] = useState<string>('ALL');

  useEffect(() => {
    loadSnapshots();
  }, [user]);

  const loadSnapshots = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchSnapshotsList(user?.institution_id || undefined);
      setSnapshots(data);
      if (data.length > 0) {
        setSelectedCandidateId(data[0].id);
      }
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('403_FORBIDDEN');
      } else {
        setError(extractErrorMessage(err, 'Failed to load snapshots.'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunReconciliation = async () => {
    if (!selectedCandidateId) return;
    try {
      setIsExecuting(true);
      setError(null);
      const res = await executeUnifiedReconciliation(
        selectedCandidateId,
        selectedBaselineId || undefined
      );
      setUnifiedResult(res);
      // Fetch detailed student trajectory items
      const items = await fetchRunResultItems(res.reconciliation_run_id);
      setStudentItems(items);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('403_FORBIDDEN');
      } else {
        setError(extractErrorMessage(err, 'Failed to execute reconciliation.'));
      }
    } finally {
      setIsExecuting(false);
    }
  };

  const filteredItems = studentItems.filter((item) => {
    if (filterClassification === 'ALL') return true;
    return item.classification === filterClassification;
  });

  if (error === '403_FORBIDDEN') {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded p-6 text-center">
          <div className="w-12 h-12 bg-red-100 text-red-700 rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-xl">
            ✕
          </div>
          <h2 className="text-base font-bold text-red-950 uppercase tracking-wide mb-2">Access Denied / प्राधिकृत नहीं</h2>
          <p className="text-xs text-red-800">
            You do not possess the statutory or institutional privileges required to inspect this cohort context.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#D7DEE5] gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                Longitudinal Engine R(t) ↔ R(t+1)
              </span>
              <span className="text-[11px] text-[#5F6B76] font-mono">Rule-Engine: APAAR-SETU-v2.0</span>
            </div>
            <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
              Longitudinal Cohort Trajectory Explorer
            </h1>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Statutory verification of student progression across consecutive academic cycles with non-punitive discrepancy intelligence.
            </p>
          </div>

          {/* Snapshot Selectors */}
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                Candidate Snapshot R(t+1)
              </label>
              <select
                value={selectedCandidateId}
                onChange={(e) => setSelectedCandidateId(e.target.value)}
                className="gov-input text-xs"
              >
                {snapshots.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.academic_year} — {s.is_authoritative ? '★ Authoritative' : 'Snapshot'} ({s.observed_headcount} stds)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                Baseline Snapshot R(t)
              </label>
              <select
                value={selectedBaselineId}
                onChange={(e) => setSelectedBaselineId(e.target.value)}
                className="gov-input text-xs"
              >
                <option value="">Auto-Detect Authoritative Prior</option>
                {snapshots
                  .filter((s) => s.id !== selectedCandidateId)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.academic_year} — {s.is_authoritative ? '★ ' : ''}
                      {s.observed_headcount} stds
                    </option>
                  ))}
              </select>
            </div>

            <div className="pt-4">
              <button
                onClick={handleRunReconciliation}
                disabled={isExecuting || !selectedCandidateId || isLoading}
                className="gov-btn-primary text-xs py-2 px-4 flex items-center gap-1.5"
              >
                {isExecuting ? 'Reconciling Cohort...' : 'Execute Reconciliation'}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs flex items-center justify-between">
            <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
            <button onClick={() => setError(null)} className="text-red-700 hover:text-red-900 font-bold ml-2">
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Metric Breakdown Cards */}
      {unifiedResult ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#23834A] shadow-sm">
              <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Continuing</span>
              <p className="text-2xl font-bold text-[#12345A] mt-1 font-mono">
                {unifiedResult.cohort_summary.continuing_count}
              </p>
              <span className="text-[10px] text-[#23834A] font-semibold">Verified Progression</span>
            </div>

            <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#174F82] shadow-sm">
              <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">New Admissions</span>
              <p className="text-2xl font-bold text-[#12345A] mt-1 font-mono">
                {unifiedResult.cohort_summary.added_count}
              </p>
              <span className="text-[10px] text-[#174F82] font-semibold">First-Year Regular</span>
            </div>

            <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#6B21A8] shadow-sm">
              <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Documented Transfers</span>
              <p className="text-2xl font-bold text-[#12345A] mt-1 font-mono">
                {unifiedResult.cohort_summary.documented_transfer_count}
              </p>
              <span className="text-[10px] text-[#6B21A8] font-semibold">Verified NOC / Proof</span>
            </div>

            <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#C0392B] shadow-sm">
              <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Unexplained App.</span>
              <p className="text-2xl font-bold text-[#C0392B] mt-1 font-mono">
                {unifiedResult.cohort_summary.unexplained_appearance_count}
              </p>
              <span className="text-[10px] text-[#C0392B] font-semibold">Regulatory Review Case</span>
            </div>

            <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#E58A24] shadow-sm">
              <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Departures / Exits</span>
              <p className="text-2xl font-bold text-[#12345A] mt-1 font-mono">
                {(unifiedResult.cohort_summary.baseline_disappearances?.WITHDRAWN || 0) +
                  (unifiedResult.cohort_summary.baseline_disappearances?.UNEXPLAINED_DISAPPEARANCE || 0)}
              </p>
              <span className="text-[10px] text-[#E58A24] font-semibold">Baseline Withdrawn / TC</span>
            </div>

            <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#8F6B00] shadow-sm">
              <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Ambiguous / Insuff.</span>
              <p className="text-2xl font-bold text-[#8F6B00] mt-1 font-mono">
                {unifiedResult.cohort_summary.ambiguous_identity_count +
                  unifiedResult.cohort_summary.insufficient_evidence_count}
              </p>
              <span className="text-[10px] text-[#8F6B00] font-semibold">Pending Identity Proof</span>
            </div>
          </div>

          {/* Classification Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-[#D7DEE5] rounded p-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-bold uppercase text-[#12345A] mr-1">Filter Trajectory:</span>
              {[
                { label: 'All Trajectories', value: 'ALL' },
                { label: 'Continuing', value: 'CONTINUING' },
                { label: 'New Admissions', value: 'ADDED' },
                { label: 'Transfers', value: 'DOCUMENTED_TRANSFER' },
                { label: 'Unexplained App.', value: 'UNEXPLAINED_APPEARANCE' },
                { label: 'Ambiguous Identity', value: 'AMBIGUOUS_IDENTITY' },
              ].map((f) => (
                <button
                  key={f.value}
                  onClick={() => setFilterClassification(f.value)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                    filterClassification === f.value
                      ? 'bg-[#12345A] text-white shadow-xs'
                      : 'bg-[#F4F6F8] hover:bg-[#EAF2F8] text-[#202B36] border border-[#D7DEE5]'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <span className="text-xs text-[#5F6B76] font-mono">
              Displaying {filteredItems.length} of {studentItems.length} student records
            </span>
          </div>

          {/* Student Trajectory Table */}
          <div className="gov-table-container">
            <div className="overflow-x-auto">
              <table className="gov-table w-full">
                <thead>
                  <tr>
                    <th className="w-12 text-center">Row</th>
                    <th>Student Name</th>
                    <th>Masked APAAR</th>
                    <th>Trajectory Classification</th>
                    <th>Review Priority</th>
                    <th>Statutory Reason & Provenance</th>
                    <th className="text-right">Case Link</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-[#5F6B76]">
                        No student observations match the selected trajectory filter.
                      </td>
                    </tr>
                  ) : (
                    filteredItems.map((item, idx) => (
                      <tr key={item.id}>
                        <td className="text-center font-mono text-[#5F6B76]">
                          {item.candidate_row_number || idx + 1}
                        </td>
                        <td className="font-semibold text-[#12345A]">{item.student_name}</td>
                        <td className="font-mono text-[#174F82] font-medium">
                          {item.masked_apaar || 'NOT AVAILABLE'}
                        </td>
                        <td>
                          <span
                            className={`gov-badge ${
                              item.classification === 'CONTINUING'
                                ? 'gov-badge-verified'
                                : item.classification === 'ADDED'
                                ? 'gov-badge-info'
                                : item.classification === 'DOCUMENTED_TRANSFER'
                                ? 'gov-badge-neutral'
                                : item.classification === 'UNEXPLAINED_APPEARANCE'
                                ? 'gov-badge-danger'
                                : 'gov-badge-warning'
                            }`}
                          >
                            {item.classification}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`gov-badge ${
                              item.review_priority === 'HIGH'
                                ? 'gov-badge-danger'
                                : item.review_priority === 'MEDIUM'
                                ? 'gov-badge-warning'
                                : 'gov-badge-neutral'
                            }`}
                          >
                            {item.review_priority}
                          </span>
                        </td>
                        <td className="text-[#202B36] max-w-sm" title={item.system_explanation}>
                          {item.system_explanation}
                        </td>
                        <td className="text-right">
                          {item.discrepancy_case_id ? (
                            <a
                              href={`/app/discrepancies?case_id=${item.discrepancy_case_id}`}
                              className="text-[#174F82] hover:text-[#12345A] font-semibold underline text-xs"
                            >
                              Inspect Case →
                            </a>
                          ) : (
                            <span className="text-[#8C9BA8] text-xs">Verified Normal</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="bg-white border border-[#D7DEE5] rounded p-12 text-center shadow-sm">
          <div className="w-14 h-14 bg-[#EAF2F8] text-[#12345A] border border-[#CBD7E3] rounded flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
            ⚖
          </div>
          <h3 className="text-base font-bold text-[#12345A] uppercase tracking-wide mb-1">
            Reconciliation Engine Ready
          </h3>
          <p className="text-xs text-[#5F6B76] max-w-md mx-auto mb-6">
            Select a candidate snapshot above and trigger the verification engine to inspect longitudinal student trajectories, transfer provenance, and intake variances under AICTE regulatory norms.
          </p>
          <button
            onClick={handleRunReconciliation}
            disabled={!selectedCandidateId || isExecuting}
            className="gov-btn-primary text-xs py-2.5 px-6"
          >
            {isExecuting ? 'Processing Cohort...' : 'Execute Unified Reconciliation'}
          </button>
        </div>
      )}
    </div>
  );
};
