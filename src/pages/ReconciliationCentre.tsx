import React, { useState, useEffect } from 'react';
import {
  Scale,
  AlertTriangle,
  XCircle,
  FileText,
  RefreshCw,
  PlusCircle,
  Database,
} from 'lucide-react';
import {
  fetchAggregateDeclarations,
  createAggregateDeclaration,
  reconcileAggregateWithRoster,
  fetchSnapshotsList,
  AggregateDeclarationItem,
  AggregateReconciliationResult,
  RosterSnapshotItem,
} from '../services/reconciliation';
import api, { extractErrorMessage } from '../services/api';

export const ReconciliationCentre: React.FC = () => {
  // State
  const [declarations, setDeclarations] = useState<AggregateDeclarationItem[]>([]);
  const [snapshots, setSnapshots] = useState<RosterSnapshotItem[]>([]);
  const [selectedDeclId, setSelectedDeclId] = useState<string>('');
  const [selectedSnapId, setSelectedSnapId] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isReconciling, setIsReconciling] = useState<boolean>(false);
  const [reconcileResult, setReconcileResult] = useState<AggregateReconciliationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // New Declaration Modal Form State
  const [showModal, setShowModal] = useState<boolean>(false);
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [programmes, setProgrammes] = useState<any[]>([]);
  const [modalInstId, setModalInstId] = useState<string>('');
  const [modalProgId, setModalProgId] = useState<string>('');
  const [modalYear, setModalYear] = useState<string>('2024-25');
  const [modalDeclaredCount, setModalDeclaredCount] = useState<number>(120);
  const [modalPopDef, setModalPopDef] = useState<string>('ALL_ENROLLED_REGULAR');
  const [modalSourceRef, setModalSourceRef] = useState<string>('AICTE-MD-2024-CSE-01');
  const [modalReportingSource, setModalReportingSource] = useState<string>('AICTE_MANDATORY_DISCLOSURE');
  const [isCreatingDecl, setIsCreatingDecl] = useState<boolean>(false);

  useEffect(() => {
    loadData();
    loadInstitutions();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [declData, snapData] = await Promise.all([
        fetchAggregateDeclarations(),
        fetchSnapshotsList(),
      ]);
      setDeclarations(declData || []);
      setSnapshots(snapData || []);

      if (declData && declData.length > 0 && !selectedDeclId) {
        setSelectedDeclId(declData[0].id);
      }
      if (snapData && snapData.length > 0 && !selectedSnapId) {
        setSelectedSnapId(snapData[0].id);
      }
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Failed to load declarations and snapshots.'));
    } finally {
      setIsLoading(false);
    }
  };

  const loadInstitutions = async () => {
    try {
      const res = await api.get('/institutions');
      const instList = res.data.items || res.data || [];
      setInstitutions(instList);
      if (instList.length > 0) {
        setModalInstId(instList[0].id);
        loadProgrammes(instList[0].id);
      }
    } catch (err) {
      console.error('Failed to load institutions:', err);
    }
  };

  const loadProgrammes = async (instId: string) => {
    try {
      const res = await api.get(`/institutions/${instId}/programmes`);
      const progList = res.data.items || res.data || [];
      setProgrammes(progList);
      if (progList.length > 0) {
        setModalProgId(progList[0].id);
      }
    } catch (err) {
      console.error('Failed to load programmes:', err);
    }
  };

  const handleReconcile = async () => {
    if (!selectedDeclId || !selectedSnapId) {
      setError('Please select both an Aggregate Declaration and an Authoritative Roster Snapshot.');
      return;
    }

    try {
      setIsReconciling(true);
      setError(null);
      const result = await reconcileAggregateWithRoster({
        declaration_id: selectedDeclId,
        snapshot_id: selectedSnapId,
        generate_discrepancy_on_variance: true,
      });
      setReconcileResult(result);
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Reconciliation failed.'));
    } finally {
      setIsReconciling(false);
    }
  };

  const handleCreateDeclaration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalInstId || !modalProgId) {
      setError('Please select institution and programme.');
      return;
    }

    try {
      setIsCreatingDecl(true);
      setError(null);
      await createAggregateDeclaration({
        institution_id: modalInstId,
        programme_id: modalProgId,
        academic_year: modalYear,
        reporting_source: modalReportingSource,
        source_reference: modalSourceRef,
        declared_count: modalDeclaredCount,
        population_definition: modalPopDef,
        student_status_definition: 'ACTIVE_ON_ROLL',
        counting_methodology: 'ACTIVE_STUDENT_CENSUS',
      });
      setShowModal(false);
      await loadData();
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Failed to create aggregate declaration.'));
    } finally {
      setIsCreatingDecl(false);
    }
  };

  const selectedDecl = declarations.find((d) => d.id === selectedDeclId);
  const selectedSnap = snapshots.find((s) => s.id === selectedSnapId);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#D7DEE5] gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                Module 9 — Historical Aggregate Reconciliation
              </span>
              <span className="text-[11px] text-[#5F6B76] font-mono">Mathematical Headcount Cross-Check</span>
            </div>
            <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
              Reconciliation Centre / सांख्यिकीय समाधान केंद्र
            </h1>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Perform rigorous comparability checks and mathematical variance reconciliation between statutory aggregate disclosures and authoritative student roster snapshots.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setShowModal(true)}
              className="gov-btn-primary text-xs py-2 px-4 flex items-center gap-1.5"
            >
              <PlusCircle size={14} />
              <span>Record Declaration</span>
            </button>
            <button
              onClick={loadData}
              disabled={isLoading}
              className="gov-btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
            >
              <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs flex items-center gap-2">
            <XCircle size={16} className="text-red-700 shrink-0" />
            <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
          </div>
        )}
      </div>

      {/* Main Reconciliation Interaction Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Source 1: Aggregate Declaration */}
        <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-[#D7DEE5]">
            <FileText size={16} className="text-[#174F82]" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#12345A]">
              1. Statutory Aggregate Disclosure / सार्वजनिक प्रकटीकरण
            </h2>
          </div>
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
              Select Declaration Record
            </label>
            <select
              value={selectedDeclId}
              onChange={(e) => setSelectedDeclId(e.target.value)}
              className="gov-input text-xs w-full"
            >
              {declarations.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.source_reference} — Declared: {d.declared_count} ({d.academic_year}, {d.population_definition})
                </option>
              ))}
            </select>
          </div>

          {selectedDecl && (
            <div className="bg-[#F4F6F8] border border-[#D7DEE5] rounded p-3 text-xs text-[#202B36] space-y-1">
              <div><span className="text-[#5F6B76]">Reporting Source:</span> <strong>{selectedDecl.reporting_source}</strong></div>
              <div><span className="text-[#5F6B76]">Academic Cycle:</span> <strong>{selectedDecl.academic_year}</strong></div>
              <div><span className="text-[#5F6B76]">Declared Headcount:</span> <strong className="font-mono text-[#12345A]">{selectedDecl.declared_count} students</strong></div>
              <div><span className="text-[#5F6B76]">Population Scope:</span> <span className="font-mono text-[11px] text-[#174F82]">{selectedDecl.population_definition}</span></div>
              <div><span className="text-[#5F6B76]">Methodology:</span> {selectedDecl.counting_methodology}</div>
            </div>
          )}
        </div>

        {/* Source 2: Authoritative Roster Snapshot */}
        <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-[#D7DEE5]">
            <Database size={16} className="text-[#23834A]" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#12345A]">
              2. Authoritative Student Roster Snapshot / प्राधिकृत पंजीयन
            </h2>
          </div>
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
              Select Roster Snapshot
            </label>
            <select
              value={selectedSnapId}
              onChange={(e) => setSelectedSnapId(e.target.value)}
              className="gov-input text-xs w-full"
            >
              {snapshots.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.academic_year} — Observed: {s.observed_headcount} ({s.snapshot_hash.slice(0, 10)}...)
                </option>
              ))}
            </select>
          </div>

          {selectedSnap && (
            <div className="bg-[#F4F6F8] border border-[#D7DEE5] rounded p-3 text-xs text-[#202B36] space-y-1">
              <div><span className="text-[#5F6B76]">Snapshot Hash:</span> <span className="font-mono text-[11px] text-[#174F82]">{selectedSnap.snapshot_hash.slice(0, 24)}...</span></div>
              <div><span className="text-[#5F6B76]">Academic Cycle:</span> <strong>{selectedSnap.academic_year}</strong></div>
              <div><span className="text-[#5F6B76]">Observed Roster Headcount:</span> <strong className="font-mono text-[#12345A]">{selectedSnap.observed_headcount} students</strong></div>
              <div><span className="text-[#5F6B76]">Population Scope:</span> {selectedSnap.snapshot_metadata?.population_definition || 'ALL_ENROLLED_REGULAR'}</div>
              <div><span className="text-[#5F6B76]">Authoritative Status:</span> <span className="gov-badge gov-badge-verified">{selectedSnap.is_authoritative ? 'Authoritative' : 'Snapshot'}</span></div>
            </div>
          )}
        </div>
      </div>

      {/* Execute Reconciliation Action */}
      <div className="text-center">
        <button
          onClick={handleReconcile}
          disabled={isReconciling || !selectedDeclId || !selectedSnapId}
          className="gov-btn-primary text-xs py-2.5 px-6 inline-flex items-center gap-2"
        >
          {isReconciling ? <RefreshCw size={14} className="animate-spin" /> : <Scale size={14} />}
          {isReconciling ? 'Evaluating Comparability & Reconciling...' : 'Execute Historical Comparability Reconciliation'}
        </button>
      </div>

      {/* Reconciliation Outcome Card */}
      {reconcileResult && (
        <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-[#D7DEE5] gap-2">
            <div>
              <span className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider block">Reconciliation Evaluation Outcome</span>
              <h2 className="text-base font-bold text-[#12345A] mt-0.5">
                Outcome: {reconcileResult.reconciliation_status || reconcileResult.outcome_status}
              </h2>
            </div>
            <div className="flex gap-2">
              <span
                className={`gov-badge ${
                  reconcileResult.comparability_status === 'COMPARABLE'
                    ? 'gov-badge-verified'
                    : 'gov-badge-warning'
                }`}
              >
                {reconcileResult.comparability_status}
              </span>
              <span
                className={`gov-badge ${
                  (reconcileResult.reconciliation_status === 'MATCH' || reconcileResult.outcome_status === 'EXACT_MATCH')
                    ? 'gov-badge-verified'
                    : (reconcileResult.reconciliation_status === 'NON_COMPARABLE' || reconcileResult.outcome_status === 'INCOMPARABLE')
                    ? 'gov-badge-neutral'
                    : 'gov-badge-danger'
                }`}
              >
                {reconcileResult.reconciliation_status || reconcileResult.outcome_status}
              </span>
            </div>
          </div>

          {/* Metric Comparison Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#12345A] shadow-xs">
              <div className="text-[10px] font-bold text-[#5F6B76] uppercase">Declared Enrolment</div>
              <div className="text-2xl font-bold text-[#12345A] font-mono mt-1">
                {reconcileResult.declared_count}
              </div>
            </div>
            <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#174F82] shadow-xs">
              <div className="text-[10px] font-bold text-[#5F6B76] uppercase">Observed Roster Headcount</div>
              <div className="text-2xl font-bold text-[#12345A] font-mono mt-1">
                {reconcileResult.roster_count}
              </div>
            </div>
            <div className={`p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 ${reconcileResult.variance === 0 ? 'border-l-[#23834A]' : 'border-l-[#C0392B]'} shadow-xs`}>
              <div className={`text-[10px] font-bold uppercase ${reconcileResult.variance === 0 ? 'text-[#23834A]' : 'text-[#C0392B]'}`}>
                Mathematical Variance
              </div>
              <div className={`text-2xl font-bold font-mono mt-1 ${reconcileResult.variance === 0 ? 'text-[#23834A]' : 'text-[#C0392B]'}`}>
                {reconcileResult.variance > 0 ? `+${reconcileResult.variance}` : reconcileResult.variance}
              </div>
            </div>
          </div>

          {/* System Explanation Banner */}
          <div className="p-3 bg-[#EAF2F8] border border-[#CBD7E3] rounded text-xs text-[#12345A] leading-relaxed">
            <strong>Regulatory Explanation:</strong> {reconcileResult.explanation}
          </div>

          {reconcileResult.discrepancy_case_id && (
            <div className="flex items-center gap-2 text-xs text-[#C0392B]">
              <AlertTriangle size={15} />
              <span>
                Discrepancy case created for audit investigation: <strong>{reconcileResult.discrepancy_case_id}</strong>
              </span>
            </div>
          )}
        </div>
      )}

      {/* Modal: Record Aggregate Declaration */}
      {showModal && (
        <div className="fixed inset-0 bg-[#0F172A]/60 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded border border-[#CBD7E3] max-w-lg w-full p-5 shadow-xl space-y-4">
            <div className="border-b border-[#D7DEE5] pb-3">
              <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
                Record Statutory Aggregate Enrolment Declaration
              </h3>
              <p className="text-xs text-[#5F6B76]">
                Enter published mandatory disclosure or annual report census figures for comparative verification.
              </p>
            </div>

            <form onSubmit={handleCreateDeclaration} className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Institution
                </label>
                <select
                  value={modalInstId}
                  onChange={(e) => {
                    setModalInstId(e.target.value);
                    loadProgrammes(e.target.value);
                  }}
                  className="gov-input text-xs w-full"
                >
                  {institutions.map((i) => (
                    <option key={i.id} value={i.id}>{i.institution_name || i.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Programme
                </label>
                <select
                  value={modalProgId}
                  onChange={(e) => setModalProgId(e.target.value)}
                  className="gov-input text-xs w-full"
                >
                  {programmes.map((p) => (
                    <option key={p.id} value={p.id}>{p.programme_name}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Academic Year
                  </label>
                  <input
                    type="text"
                    value={modalYear}
                    onChange={(e) => setModalYear(e.target.value)}
                    className="gov-input text-xs w-full"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Declared Headcount
                  </label>
                  <input
                    type="number"
                    value={modalDeclaredCount}
                    onChange={(e) => setModalDeclaredCount(parseInt(e.target.value, 10))}
                    className="gov-input font-mono text-xs w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Population Definition
                </label>
                <select
                  value={modalPopDef}
                  onChange={(e) => setModalPopDef(e.target.value)}
                  className="gov-input text-xs w-full"
                >
                  <option value="ALL_ENROLLED_REGULAR">ALL_ENROLLED_REGULAR (All active regular students)</option>
                  <option value="FIRST_YEAR_ONLY">FIRST_YEAR_ONLY (Fresh entry batch)</option>
                  <option value="PART_TIME_ONLY">PART_TIME_ONLY (Non-comparable regular cohort)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Reporting Source
                </label>
                <select
                  value={modalReportingSource}
                  onChange={(e) => setModalReportingSource(e.target.value)}
                  className="gov-input text-xs w-full"
                >
                  <option value="AICTE_MANDATORY_DISCLOSURE">AICTE Mandatory Disclosure</option>
                  <option value="ANNUAL_REPORT">Institutional Annual Report</option>
                  <option value="STATE_DTE_RETURNS">State DTE Returns</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Source Reference / Disclosure ID
                </label>
                <input
                  type="text"
                  value={modalSourceRef}
                  onChange={(e) => setModalSourceRef(e.target.value)}
                  className="gov-input font-mono text-xs w-full"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#D7DEE5]">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="gov-btn-secondary text-xs py-1.5 px-3"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingDecl}
                  className="gov-btn-primary text-xs py-1.5 px-4"
                >
                  {isCreatingDecl ? 'Saving...' : 'Record Declaration'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
