import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  Shield,
} from 'lucide-react';
import api, { extractErrorMessage } from '../services/api';

export const ReviewResolution: React.FC = () => {
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [actionChoice, setActionChoice] = useState<string>('RESOLVE_WITH_EVIDENCE');
  const [mandatoryReason, setMandatoryReason] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.get('/discrepancies/cases', { params: { limit: 50 } });
      const items = res.data.items || [];
      setCases(items);
      if (items.length > 0 && !selectedCase) {
        setSelectedCase(items[0]);
      }
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Failed to load discrepancy cases.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRecordDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;
    if (!mandatoryReason.trim()) {
      setError('A mandatory regulatory justification reason is required.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setFeedback(null);
      await api.post(`/discrepancies/cases/${selectedCase.id}/decisions`, {
        action: actionChoice,
        mandatory_reason: mandatoryReason.trim(),
        evidence_references: {
          reviewer_source: 'REGULATORY_WORKBENCH',
          reviewed_at: new Date().toISOString(),
        },
      });
      setFeedback('Decision recorded and chained to immutable audit ledger successfully.');
      setMandatoryReason('');
      await loadCases();
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Failed to record decision.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="gov-badge gov-badge-info">
            Statutory Resolution Workbench
          </span>
          <span className="text-[11px] text-[#5F6B76] font-mono">Module 11 — Due-Process Review</span>
        </div>
        <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
          Regulatory Inquiry & Review Workbench / समीक्षा एवं समाधान पीठ
        </h1>
        <p className="text-xs text-[#5F6B76] mt-0.5">
          Authorised human inquiry portal for recording reasoned determinations, institutional evidence submissions, and versioned corrections without mutating original historical rosters.
        </p>
      </div>

      {feedback && (
        <div className="p-3 bg-[#EAF7EE] border border-[#23834A] rounded text-[#166534] text-xs font-semibold flex items-center gap-2">
          <span>✓</span>
          <span>{feedback}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs flex items-center gap-2">
          <span>✕</span>
          <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
        </div>
      )}

      {/* Two Column Layout: Left: Cases List, Right: Inquiry & Resolution Console */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Cases List */}
        <div className="lg:col-span-5 bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center pb-3 border-b border-[#D7DEE5]">
            <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Active Regulatory Dockets ({cases.length})
            </h2>
            <button
              onClick={loadCases}
              disabled={isLoading}
              className="gov-btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            >
              <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>

          <div className="space-y-2.5 max-h-[620px] overflow-y-auto pr-1">
            {cases.length === 0 ? (
              <div className="text-center py-12 text-[#5F6B76] text-xs">
                No active discrepancy cases found.
              </div>
            ) : (
              cases.map((c) => {
                const isSelected = selectedCase?.id === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => setSelectedCase(c)}
                    className={`p-3.5 rounded border cursor-pointer transition ${
                      isSelected
                        ? 'border-[#174F82] bg-[#EAF2F8] border-l-4 border-l-[#12345A] shadow-xs'
                        : 'border-[#D7DEE5] bg-white hover:bg-[#F4F6F8]'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs font-bold font-mono text-[#12345A]">
                        {c.case_number}
                      </span>
                      <span
                        className={`gov-badge ${
                          c.case_status === 'OPEN'
                            ? 'gov-badge-warning'
                            : c.case_status === 'RESOLVED' || c.case_status === 'VERIFIED_VALID'
                            ? 'gov-badge-verified'
                            : 'gov-badge-info'
                        }`}
                      >
                        {c.case_status}
                      </span>
                    </div>

                    <div className="text-xs font-semibold text-[#202B36] mb-1">
                      {c.classification.replace(/_/g, ' ')}
                    </div>
                    <div className="text-[11px] text-[#5F6B76] flex items-center justify-between">
                      <span>Priority: <strong className="text-[#12345A]">{c.review_priority}</strong></span>
                      <span className="font-mono">Year: {c.academic_year}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Case Dossier & Resolution Form */}
        <div className="lg:col-span-7 bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
          {selectedCase ? (
            <div className="space-y-5">
              <div className="border-b border-[#D7DEE5] pb-4">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#5F6B76]">
                  Regulatory Docket Inspection Dossier
                </span>
                <h2 className="text-lg font-bold text-[#12345A] mt-0.5 font-mono">
                  {selectedCase.case_number}
                </h2>
                <div className="text-xs text-[#5F6B76] mt-0.5">
                  Trajectory Classification: <strong className="text-[#12345A]">{selectedCase.classification}</strong>
                </div>
              </div>

              {/* Scope & Details */}
              <div className="bg-[#F4F6F8] border border-[#D7DEE5] rounded p-3.5 text-xs text-[#202B36] grid grid-cols-2 gap-2">
                <div><span className="text-[#5F6B76]">Scope Context:</span> <strong className="text-[#12345A]">{selectedCase.scope_type || 'STUDENT_COHORT'}</strong></div>
                <div><span className="text-[#5F6B76]">Academic Cycle:</span> <strong className="text-[#12345A]">{selectedCase.academic_year}</strong></div>
                <div><span className="text-[#5F6B76]">Docket Status:</span> <strong className="text-[#12345A]">{selectedCase.case_status}</strong></div>
                <div><span className="text-[#5F6B76]">Review Priority:</span> <strong className="text-[#12345A]">{selectedCase.review_priority}</strong></div>
              </div>

              {/* Regulatory Action Decision Form */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-[#12345A] uppercase tracking-wide">
                  Record Regulatory Determination / प्राधिकृत निर्णय दर्ज करें
                </h3>
                <form onSubmit={handleRecordDecision} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                      Determination Action
                    </label>
                    <select
                      value={actionChoice}
                      onChange={(e) => setActionChoice(e.target.value)}
                      className="gov-input text-xs w-full"
                    >
                      <option value="RESOLVE_WITH_EVIDENCE">RESOLVE_WITH_EVIDENCE (Legitimate documented explanation provided)</option>
                      <option value="CONFIRM_DISCREPANCY">CONFIRM_DISCREPANCY (Confirmed statutory violation)</option>
                      <option value="REQUEST_INSTITUTION_EVIDENCE">REQUEST_INSTITUTION_EVIDENCE (Issue notice to institution)</option>
                      <option value="CLOSE_FALSE_POSITIVE">CLOSE_FALSE_POSITIVE (Algorithmic or data false positive)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                      Mandatory Regulatory Justification (Audit Protected)
                    </label>
                    <textarea
                      rows={4}
                      value={mandatoryReason}
                      onChange={(e) => setMandatoryReason(e.target.value)}
                      placeholder="Enter detailed statutory reasoning and citations for this determination..."
                      className="gov-input text-xs w-full font-mono"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="gov-btn-primary text-xs py-2 px-5 flex items-center gap-2"
                  >
                    {isSubmitting ? <RefreshCw size={14} className="animate-spin" /> : <Shield size={14} />}
                    {isSubmitting ? 'Recording Decision...' : 'Commit Reasoned Determination'}
                  </button>
                </form>
              </div>
            </div>
          ) : (
            <div className="text-center py-20 text-[#5F6B76] text-xs">
              Select a discrepancy case from the docket list to inspect evidence and record a determination.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
