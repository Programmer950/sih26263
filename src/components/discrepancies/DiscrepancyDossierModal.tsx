import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import {
  DiscrepancyCase,
  DecisionAction,
  CaseStatus,
} from '../../types/discrepancy';
import {
  X,
  ShieldCheck,
  AlertTriangle,
  Clock,
  FileText,
  User,
  ArrowRight,
  CheckCircle2,
  Hash,
  Send,
  Lock,
} from 'lucide-react';

interface Props {
  caseItem: DiscrepancyCase;
  isOpen: boolean;
  onClose: () => void;
  onCaseUpdated: (updatedCase: DiscrepancyCase) => void;
}

export const DiscrepancyDossierModal: React.FC<Props> = ({
  caseItem,
  isOpen,
  onClose,
  onCaseUpdated,
}) => {
  const { user } = useAuth();
  const [selectedAction, setSelectedAction] = useState<DecisionAction>('START_INVESTIGATION');
  const [reason, setReason] = useState('');
  const [evidenceRef, setEvidenceRef] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'evidence' | 'timeline' | 'action'>('evidence');

  if (!isOpen) return null;

  const userRole = typeof user?.role === 'string' ? user.role : (user?.role as any)?.role_name || '';
  const isReviewer = userRole === 'REGULATORY_REVIEWER' || userRole === 'SYSTEM_ADMIN';
  const isInstitution = userRole === 'INSTITUTION_ADMIN';

  // Determine available actions based on role and current case status
  const getAvailableActions = (): DecisionAction[] => {
    if (caseItem.case_status === 'CLOSED' || caseItem.case_status === 'VERIFIED_VALID') {
      return isReviewer ? ['REOPEN_CASE'] : [];
    }

    if (isReviewer) {
      if (caseItem.case_status === 'OPEN') {
        return ['START_INVESTIGATION', 'CONFIRM_VALID'];
      }
      if (
        caseItem.case_status === 'UNDER_INVESTIGATION' ||
        caseItem.case_status === 'INVESTIGATING' ||
        caseItem.case_status === 'EXPLANATION_SUBMITTED'
      ) {
        return ['REQUEST_EVIDENCE', 'RECORD_CORRECTION', 'CONFIRM_VALID', 'CLOSE_CASE'];
      }
      if (caseItem.case_status === 'EVIDENCE_REQUESTED') {
        return ['CLOSE_CASE', 'CONFIRM_VALID'];
      }
      if (
        caseItem.case_status === 'CORRECTION_SUBMITTED' ||
        caseItem.case_status === 'CORRECTION_RECORDED'
      ) {
        return ['CONFIRM_VALID', 'CLOSE_CASE'];
      }
    }

    if (isInstitution) {
      if (
        caseItem.case_status === 'EVIDENCE_REQUESTED' ||
        caseItem.case_status === 'UNDER_INVESTIGATION' ||
        caseItem.case_status === 'INVESTIGATING'
      ) {
        return ['SUBMIT_EXPLANATION'];
      }
    }

    return [];
  };

  const availableActions = getAvailableActions();

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (reason.trim().length < 10) {
      setErrorMsg('Mandatory reason must be at least 10 characters in length.');
      return;
    }

    setSubmitting(true);
    try {
      await api.post(`/discrepancies/cases/${caseItem.id}/decisions`, {
        action: selectedAction,
        mandatory_reason: reason.trim(),
        supporting_evidence_ref: evidenceRef.trim() || undefined,
      });

      // Refresh case detail
      const refreshed = await api.get(`/discrepancies/cases/${caseItem.id}`);
      onCaseUpdated(refreshed.data);
      setReason('');
      setEvidenceRef('');
      setActiveTab('timeline');
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Failed to record decision.';
      setErrorMsg(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const getPriorityBadgeClass = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'LOW':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const getStatusBadgeClass = (status: CaseStatus) => {
    switch (status) {
      case 'OPEN':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'UNDER_INVESTIGATION':
      case 'INVESTIGATING':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'EVIDENCE_REQUESTED':
        return 'bg-orange-50 text-orange-700 border-orange-200';
      case 'EXPLANATION_SUBMITTED':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'CORRECTION_SUBMITTED':
      case 'CORRECTION_RECORDED':
        return 'bg-teal-50 text-teal-700 border-teal-200';
      case 'VERIFIED_VALID':
      case 'CLOSED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in-50 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-50 border border-indigo-100 rounded-lg text-indigo-700">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-semibold text-slate-900 tracking-tight">
                  Evidence Dossier: {caseItem.case_number}
                </h3>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getPriorityBadgeClass(
                    caseItem.priority
                  )}`}
                >
                  {caseItem.priority} Priority
                </span>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getStatusBadgeClass(
                    caseItem.case_status
                  )}`}
                >
                  {caseItem.case_status.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Deterministic finding generated by Reconciliation Engine v1.0.0
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab navigation */}
        <div className="flex border-b border-slate-200 px-6 bg-white text-xs font-medium text-slate-600">
          <button
            onClick={() => setActiveTab('evidence')}
            className={`py-3 px-4 border-b-2 transition-colors ${
              activeTab === 'evidence'
                ? 'border-indigo-600 text-indigo-700 font-semibold'
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            Evidence & Provenance
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={`py-3 px-4 border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeTab === 'timeline'
                ? 'border-indigo-600 text-indigo-700 font-semibold'
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <span>Decision Audit Trail</span>
            <span className="px-1.5 py-0.2 bg-slate-100 rounded-full text-[11px] font-bold text-slate-600">
              {caseItem.decisions?.length || 0}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('action')}
            className={`py-3 px-4 border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeTab === 'action'
                ? 'border-indigo-600 text-indigo-700 font-semibold'
                : 'border-transparent hover:text-slate-900'
            }`}
          >
            <span>Administrative Action</span>
            {availableActions.length > 0 && (
              <span className="w-2 h-2 rounded-full bg-indigo-600" />
            )}
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50">
          {/* TAB 1: Evidence & Provenance */}
          {activeTab === 'evidence' && (
            <div className="space-y-6">
              {/* Neutral Classification Rationale Card */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                <div className="flex items-start space-x-3">
                  <div className="p-2 bg-amber-50 text-amber-700 rounded-md mt-0.5">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Objective Classification: {caseItem.classification.replace(/_/g, ' ')}
                    </h4>
                    <p className="text-sm text-slate-700 mt-1 leading-relaxed">
                      {caseItem.system_notes ||
                        'Comparative longitudinal analysis detected an unreconciled cohort variation requiring institutional verification.'}
                    </p>
                    <div className="mt-2 text-[11px] text-slate-500 flex items-center space-x-4">
                      <span>Occurrences Observed: <strong className="text-slate-700">{caseItem.occurrence_count}</strong></span>
                      <span>Academic Year: <strong className="text-slate-700">{caseItem.academic_year}</strong></span>
                      <span>Lineage Status: <strong className="text-slate-700">{caseItem.linked_prior_case_id ? 'Recurring' : 'Initial'}</strong></span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Student Identity and Sensitive Evidence Protection */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Student Identity & Privacy Masking</span>
                </h4>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-slate-500 font-medium">Reported Full Name</div>
                    <div className="text-sm font-semibold text-slate-900 mt-0.5 flex items-center space-x-1.5">
                      <User className="w-3.5 h-3.5 text-slate-400" />
                      <span>{caseItem.student_name}</span>
                    </div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-slate-500 font-medium">Masked APAAR Reference</div>
                    <div className="text-sm font-mono font-semibold text-indigo-700 mt-0.5 flex items-center space-x-1.5">
                      <Lock className="w-3.5 h-3.5 text-indigo-500" />
                      <span>{caseItem.masked_apaar}</span>
                    </div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 col-span-2">
                    <div className="text-slate-500 font-medium">Student Identity UUID (Internal)</div>
                    <div className="text-xs font-mono text-slate-600 mt-0.5 select-all">
                      {caseItem.student_identity_id}
                    </div>
                  </div>
                </div>
              </div>

              {/* Immutable Provenance Audit */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center space-x-2">
                  <Hash className="w-4 h-4 text-slate-600" />
                  <span>Reconciliation Run Lineage</span>
                </h4>
                <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                  <div className="p-3 bg-slate-50 rounded border border-slate-200">
                    <span className="text-slate-500 font-sans block text-[11px]">Initial Reconciliation Run</span>
                    <span className="text-slate-700 select-all block mt-1 break-all">
                      {caseItem.initial_reconciliation_run_id}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded border border-slate-200">
                    <span className="text-slate-500 font-sans block text-[11px]">Latest Reconciliation Run</span>
                    <span className="text-slate-700 select-all block mt-1 break-all">
                      {caseItem.latest_reconciliation_run_id}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Decision Audit Trail */}
          {activeTab === 'timeline' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Append-Only Decision History
                </h4>
                <span className="text-xs text-slate-500">
                  Total Recorded Events: {caseItem.decisions?.length || 0}
                </span>
              </div>

              {(!caseItem.decisions || caseItem.decisions.length === 0) ? (
                <div className="text-center py-12 bg-white rounded-lg border border-dashed border-slate-300">
                  <Clock className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-medium text-slate-600">No decisions recorded yet</p>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                    This discrepancy case is currently in {caseItem.case_status} status. Authorized officers can record reasoned determinations.
                  </p>
                </div>
              ) : (
                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
                  {caseItem.decisions.map((dec, idx) => (
                    <div key={dec.id || idx} className="relative group">
                      {/* Timeline dot */}
                      <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-white border-2 border-indigo-600 flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                      </div>

                      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm hover:border-slate-300 transition-colors">
                        <div className="flex items-center justify-between text-xs mb-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-slate-900">{dec.action.replace(/_/g, ' ')}</span>
                            <span className="text-slate-400">•</span>
                            <div className="flex items-center space-x-1 font-mono text-[11px] text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                              <span>{dec.prior_status}</span>
                              <ArrowRight className="w-3 h-3 text-slate-400" />
                              <span className="font-semibold text-indigo-700">{dec.new_status}</span>
                            </div>
                          </div>
                          <span className="text-slate-400 text-[11px]">
                            {new Date(dec.created_at).toLocaleString()}
                          </span>
                        </div>

                        <p className="text-xs text-slate-700 bg-slate-50 p-2.5 rounded border border-slate-100 leading-relaxed font-sans">
                          "{dec.decision_reason}"
                        </p>

                        {dec.supporting_evidence_ref && (
                          <div className="mt-2 text-[11px] text-indigo-600 flex items-center space-x-1">
                            <FileText className="w-3 h-3" />
                            <span>Evidence Ref: {dec.supporting_evidence_ref}</span>
                          </div>
                        )}

                        <div className="mt-2 pt-2 border-t border-slate-100 text-[10px] text-slate-400 flex items-center justify-between">
                          <span>Recorded by: {dec.recorded_by_email || dec.recorded_by_user_id}</span>
                          <span className="font-mono">ID: {dec.id?.slice(0, 8)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Administrative Action */}
          {activeTab === 'action' && (
            <div className="space-y-4">
              <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                <h4 className="text-sm font-semibold text-slate-900 mb-1">
                  Record Determinations & Transition Status
                </h4>
                <p className="text-xs text-slate-500 mb-4">
                  All administrative actions require a mandatory reasoned explanation (min. 10 chars) and are appended to the immutable audit chain.
                </p>

                {availableActions.length === 0 ? (
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-center text-xs text-slate-600">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto mb-1" />
                    <p className="font-medium text-slate-800">
                      No further administrative actions permitted for current status ({caseItem.case_status}).
                    </p>
                    <p className="text-slate-500 mt-0.5">
                      Case is resolved or pending actions from another regulatory authority.
                    </p>
                  </div>
                ) : (
                  <form onSubmit={handleDecisionSubmit} className="space-y-4">
                    {errorMsg && (
                      <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-start space-x-2">
                        <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                        <span>{errorMsg}</span>
                      </div>
                    )}

                    {/* Action Selector */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                        Select Action
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {availableActions.map((act) => (
                          <button
                            key={act}
                            type="button"
                            onClick={() => setSelectedAction(act)}
                            className={`p-2.5 rounded-lg border text-left text-xs transition-all ${
                              selectedAction === act
                                ? 'border-indigo-600 bg-indigo-50/50 text-indigo-900 font-semibold ring-1 ring-indigo-600'
                                : 'border-slate-200 hover:border-slate-300 text-slate-700 bg-white'
                            }`}
                          >
                            <div>{act.replace(/_/g, ' ')}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Mandatory Reason */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
                          Mandatory Reason / Institutional Response *
                        </label>
                        <span
                          className={`text-[11px] ${
                            reason.trim().length >= 10 ? 'text-emerald-600' : 'text-slate-400'
                          }`}
                        >
                          {reason.trim().length}/10 chars min
                        </span>
                      </div>
                      <textarea
                        rows={3}
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Provide detailed justification or rationale for this determination..."
                        className="w-full text-xs rounded-lg border border-slate-300 p-2.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white"
                        required
                      />
                    </div>

                    {/* Supporting Evidence Ref */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                        Supporting Evidence Reference (Optional)
                      </label>
                      <input
                        type="text"
                        value={evidenceRef}
                        onChange={(e) => setEvidenceRef(e.target.value)}
                        placeholder="e.g. DOC-VERIFY-2024-001 or URL/Ticket ID"
                        className="w-full text-xs rounded-lg border border-slate-300 p-2 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white"
                      />
                    </div>

                    {/* Submit button */}
                    <div className="flex justify-end pt-2">
                      <button
                        type="submit"
                        disabled={submitting || reason.trim().length < 10}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1.5 transition-colors shadow-sm"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>{submitting ? 'Recording Decision...' : 'Commit Immutable Determination'}</span>
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-white flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
          >
            Close Dossier
          </button>
        </div>
      </div>
    </div>
  );
};
