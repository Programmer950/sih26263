import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  DiscrepancyCase,
  CaseStatus,
  ReviewPriority,
  ReconciliationRun,
} from '../types/discrepancy';
import { DiscrepancyDossierModal } from '../components/discrepancies/DiscrepancyDossierModal';
import {
  AlertTriangle,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  Layers,
  ShieldCheck,
  RefreshCw,
  Lock,
  User,
  Fingerprint,
} from 'lucide-react';

export const DiscrepancyDashboard: React.FC = () => {
  const [cases, setCases] = useState<DiscrepancyCase[]>([]);
  const [totalCases, setTotalCases] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [classFilter, setClassFilter] = useState<string>('ALL');

  // Modal Dossier
  const [selectedCase, setSelectedCase] = useState<DiscrepancyCase | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Reconciliation Runs View
  const [showRunsView, setShowRunsView] = useState(false);
  const [runs, setRuns] = useState<ReconciliationRun[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (priorityFilter !== 'ALL') params.priority = priorityFilter;
      if (classFilter !== 'ALL') params.classification = classFilter;

      const res = await api.get('/discrepancies/cases', { params });
      setCases(res.data.items || []);
      setTotalCases(res.data.total || 0);
    } catch (err) {
      console.error('Failed to load discrepancy cases', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRuns = async () => {
    setLoadingRuns(true);
    try {
      const res = await api.get('/reconciliation/runs', { params: { limit: 20 } });
      setRuns(res.data.items || []);
    } catch (err) {
      console.error('Failed to load reconciliation runs', err);
    } finally {
      setLoadingRuns(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [statusFilter, priorityFilter, classFilter]);

  useEffect(() => {
    if (showRunsView) {
      fetchRuns();
    }
  }, [showRunsView]);

  const handleOpenDossier = (c: DiscrepancyCase) => {
    setSelectedCase(c);
    setModalOpen(true);
  };

  const handleCaseUpdated = (updated: DiscrepancyCase) => {
    setCases((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    if (selectedCase?.id === updated.id) {
      setSelectedCase(updated);
    }
  };

  // Filter in-memory by search term
  const filteredCases = cases.filter((c) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      c.case_number.toLowerCase().includes(term) ||
      c.student_name.toLowerCase().includes(term) ||
      c.masked_apaar.toLowerCase().includes(term) ||
      c.classification.toLowerCase().includes(term)
    );
  });

  // Calculate Metrics
  const highPriorityCount = cases.filter((c) => c.priority === 'HIGH').length;
  const inReviewCount = cases.filter((c) =>
    ['UNDER_INVESTIGATION', 'INVESTIGATING', 'EVIDENCE_REQUESTED', 'EXPLANATION_SUBMITTED'].includes(c.case_status)
  ).length;
  const resolvedCount = cases.filter((c) =>
    ['VERIFIED_VALID', 'CLOSED'].includes(c.case_status)
  ).length;
  const openCount = cases.filter((c) => c.case_status === 'OPEN').length;

  const getPriorityBadge = (priority: ReviewPriority) => {
    switch (priority) {
      case 'HIGH':
        return <span className="gov-badge gov-badge-danger">HIGH</span>;
      case 'MEDIUM':
        return <span className="gov-badge gov-badge-warning">MEDIUM</span>;
      case 'LOW':
        return <span className="gov-badge gov-badge-info">LOW</span>;
      default:
        return <span className="gov-badge gov-badge-neutral">NONE</span>;
    }
  };

  const getStatusBadge = (status: CaseStatus) => {
    switch (status) {
      case 'OPEN':
        return <span className="gov-badge gov-badge-warning">OPEN</span>;
      case 'UNDER_INVESTIGATION':
      case 'INVESTIGATING':
        return <span className="gov-badge gov-badge-info">UNDER INVESTIGATION</span>;
      case 'EVIDENCE_REQUESTED':
        return <span className="gov-badge gov-badge-warning">EVIDENCE REQUESTED</span>;
      case 'EXPLANATION_SUBMITTED':
        return <span className="gov-badge gov-badge-info">EXPLANATION SUBMITTED</span>;
      case 'CORRECTION_SUBMITTED':
      case 'CORRECTION_RECORDED':
        return <span className="gov-badge gov-badge-info">CORRECTION SUBMITTED</span>;
      case 'VERIFIED_VALID':
        return <span className="gov-badge gov-badge-verified">VERIFIED VALID</span>;
      case 'CLOSED':
        return <span className="gov-badge gov-badge-neutral">CLOSED</span>;
      default:
        return <span className="gov-badge gov-badge-neutral">{status}</span>;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#D7DEE5] gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                Regulatory Discrepancy Registry
              </span>
              <span className="text-[11px] text-[#5F6B76] font-mono">Engine: APAAR-SETU-v2.0</span>
            </div>
            <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
              Discrepancy Intelligence & Verification Centre / विसंगति निवारण केंद्र
            </h1>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Objective cohort reconciliation and case management. Investigates unexplained appearances, departures, and identity ambiguities without presumption of non-compliance.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowRunsView(!showRunsView)}
              className="gov-btn-secondary text-xs py-2 px-3.5 flex items-center gap-1.5"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>{showRunsView ? 'View Case Ledger' : 'Reconciliation Runs'}</span>
            </button>
            <button
              onClick={fetchCases}
              className="gov-btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
              title="Refresh Ledger"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#E58A24] shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">
              Active Cases
            </span>
            <AlertTriangle className="w-4 h-4 text-[#E58A24]" />
          </div>
          <div className="text-2xl font-bold text-[#12345A] mt-1 font-mono">{openCount}</div>
          <p className="text-[10px] text-[#5F6B76] mt-0.5">Pending inquiry or assignment</p>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#C0392B] shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">
              High Priority
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-[#C0392B]" />
          </div>
          <div className="text-2xl font-bold text-[#C0392B] mt-1 font-mono">{highPriorityCount}</div>
          <p className="text-[10px] text-[#5F6B76] mt-0.5">Unexplained cohort variations</p>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#174F82] shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">
              Under Review
            </span>
            <Clock className="w-4 h-4 text-[#174F82]" />
          </div>
          <div className="text-2xl font-bold text-[#174F82] mt-1 font-mono">{inReviewCount}</div>
          <p className="text-[10px] text-[#5F6B76] mt-0.5">Evidence requested / submitted</p>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#23834A] shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">
              Resolved Cases
            </span>
            <CheckCircle2 className="w-4 h-4 text-[#23834A]" />
          </div>
          <div className="text-2xl font-bold text-[#23834A] mt-1 font-mono">{resolvedCount}</div>
          <p className="text-[10px] text-[#5F6B76] mt-0.5">Verified valid or closed with rationale</p>
        </div>
      </div>

      {/* VIEW 1: Case Ledger View */}
      {!showRunsView && (
        <div className="bg-white rounded border border-[#D7DEE5] shadow-sm overflow-hidden">
          {/* Controls Bar */}
          <div className="p-4 border-b border-[#D7DEE5] flex flex-col md:flex-row gap-3 items-center justify-between bg-[#F4F6F8]">
            {/* Search Input */}
            <div className="relative w-full md:w-80">
              <Search className="w-3.5 h-3.5 text-[#5F6B76] absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search case #, student name, APAAR..."
                className="gov-input pl-8 text-xs w-full"
              />
            </div>

            {/* Filter Dropdowns */}
            <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
              <div className="flex items-center space-x-1 text-xs text-[#5F6B76]">
                <Filter className="w-3 h-3" />
                <span className="font-semibold text-[11px] uppercase">Filter:</span>
              </div>

              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="gov-input text-xs py-1 px-2"
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="UNDER_INVESTIGATION">Under Investigation</option>
                <option value="EVIDENCE_REQUESTED">Evidence Requested</option>
                <option value="EXPLANATION_SUBMITTED">Explanation Submitted</option>
                <option value="CORRECTION_SUBMITTED">Correction Submitted</option>
                <option value="VERIFIED_VALID">Verified Valid</option>
                <option value="CLOSED">Closed</option>
              </select>

              {/* Priority Filter */}
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="gov-input text-xs py-1 px-2"
              >
                <option value="ALL">All Priorities</option>
                <option value="HIGH">High Priority</option>
                <option value="MEDIUM">Medium Priority</option>
                <option value="LOW">Low Priority</option>
              </select>

              {/* Classification Filter */}
              <select
                value={classFilter}
                onChange={(e) => setClassFilter(e.target.value)}
                className="gov-input text-xs py-1 px-2"
              >
                <option value="ALL">All Classifications</option>
                <option value="UNEXPLAINED_APPEARANCE">Unexplained Appearance</option>
                <option value="UNEXPLAINED_DISAPPEARANCE">Unexplained Disappearance</option>
                <option value="AMBIGUOUS_IDENTITY">Ambiguous Identity</option>
                <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="gov-table-container border-0 rounded-none">
            <table className="gov-table w-full">
              <thead>
                <tr>
                  <th>Case Number</th>
                  <th>Student & Masked APAAR</th>
                  <th>Classification</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th className="text-center">Occurrences</th>
                  <th>Observed Date</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-[#5F6B76]">
                      Loading discrepancy cases from secure ledger...
                    </td>
                  </tr>
                ) : filteredCases.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-[#5F6B76]">
                      <ShieldCheck className="w-8 h-8 text-[#23834A] mx-auto mb-2" />
                      <p className="font-semibold text-[#12345A]">No matching discrepancy findings</p>
                      <p className="text-xs text-[#5F6B76] mt-0.5">
                        All student cohorts are reconciled or no cases match current filters.
                      </p>
                    </td>
                  </tr>
                ) : (
                  filteredCases.map((c) => (
                    <tr key={c.id}>
                      <td className="font-mono font-bold text-[#12345A]">
                        {c.case_number}
                      </td>
                      <td>
                        <div className="font-semibold text-[#12345A] flex items-center space-x-1.5">
                          <User className="w-3.5 h-3.5 text-[#5F6B76]" />
                          <span>{c.student_name}</span>
                        </div>
                        <div className="text-[11px] font-mono text-[#174F82] flex items-center space-x-1 mt-0.5">
                          <Lock className="w-3 h-3 text-[#5F6B76]" />
                          <span>{c.masked_apaar}</span>
                        </div>
                      </td>
                      <td>
                        <span className="font-medium text-[#202B36]">
                          {c.classification.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td>{getPriorityBadge(c.priority)}</td>
                      <td>{getStatusBadge(c.case_status)}</td>
                      <td className="text-center font-mono font-bold text-[#12345A]">
                        {c.occurrence_count}
                      </td>
                      <td className="text-[#5F6B76] text-xs">
                        {new Date(c.latest_observed_at).toLocaleDateString()}
                      </td>
                      <td className="text-right">
                        <button
                          onClick={() => handleOpenDossier(c)}
                          className="gov-btn-secondary text-xs py-1 px-3"
                        >
                          View Dossier
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="p-3 border-t border-[#D7DEE5] bg-[#F4F6F8] text-xs text-[#5F6B76] flex justify-between items-center">
            <span>Displaying {filteredCases.length} of {totalCases} registered findings</span>
            <span className="font-mono text-[11px] text-[#12345A] font-semibold">Strict multi-tenant security active</span>
          </div>
        </div>
      )}

      {/* VIEW 2: Reconciliation Runs View */}
      {showRunsView && (
        <div className="bg-white rounded border border-[#D7DEE5] shadow-sm overflow-hidden">
          <div className="p-4 border-b border-[#D7DEE5] bg-[#F4F6F8] flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
                Deterministic Reconciliation Executions / समाधान रिकॉर्ड
              </h3>
              <p className="text-xs text-[#5F6B76] mt-0.5">
                Audit log of executed comparisons, cryptographic fingerprints, and case yield.
              </p>
            </div>
            <button
              onClick={fetchRuns}
              className="gov-btn-secondary text-xs py-1 px-3"
            >
              Refresh Runs
            </button>
          </div>

          <div className="gov-table-container border-0 rounded-none">
            <table className="gov-table w-full">
              <thead>
                <tr>
                  <th>Run ID / Type</th>
                  <th>Academic Year</th>
                  <th>Candidate Snapshot</th>
                  <th>Baseline Snapshot</th>
                  <th>Summary Breakdown</th>
                  <th>Result SHA-256 Digest</th>
                  <th className="text-right">Executed At</th>
                </tr>
              </thead>
              <tbody>
                {loadingRuns ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-[#5F6B76]">
                      Loading run audit records...
                    </td>
                  </tr>
                ) : runs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-[#5F6B76]">
                      No reconciliation runs recorded yet.
                    </td>
                  </tr>
                ) : (
                  runs.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <div className="font-mono font-bold text-[#12345A]">
                          {r.id.slice(0, 8)}...
                        </div>
                        <div className="text-[11px] text-[#5F6B76] mt-0.5">
                          {r.run_type.replace(/_/g, ' ')}
                        </div>
                      </td>
                      <td className="font-semibold text-[#12345A]">
                        {r.academic_year}
                      </td>
                      <td className="font-mono text-xs text-[#174F82]">
                        {r.candidate_snapshot_id.slice(0, 8)}...
                      </td>
                      <td className="font-mono text-xs text-[#5F6B76]">
                        {r.baseline_snapshot_id ? `${r.baseline_snapshot_id.slice(0, 8)}...` : 'Auto / None'}
                      </td>
                      <td>
                        <div className="flex flex-wrap gap-1 text-[10px]">
                          {r.summary_counts && Object.entries(r.summary_counts).slice(0, 4).map(([k, v]) => (
                            <span key={k} className="px-1.5 py-0.5 bg-[#EAF2F8] border border-[#CBD7E3] rounded text-[#12345A] font-medium">
                              {k}: <strong>{v}</strong>
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <div className="font-mono text-xs text-[#174F82] flex items-center space-x-1" title={r.result_fingerprint}>
                          <Fingerprint className="w-3.5 h-3.5 text-[#174F82]" />
                          <span>{r.result_fingerprint.slice(0, 12)}...</span>
                        </div>
                      </td>
                      <td className="text-right text-[#5F6B76] text-xs">
                        {new Date(r.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Interactive Dossier Modal */}
      {selectedCase && (
        <DiscrepancyDossierModal
          caseItem={selectedCase}
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          onCaseUpdated={handleCaseUpdated}
        />
      )}
    </div>
  );
};

export default DiscrepancyDashboard;
