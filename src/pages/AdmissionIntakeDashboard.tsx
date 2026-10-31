import React, { useState, useEffect } from 'react';
import api, { extractErrorMessage } from '../services/api';
import {
  ApprovalConfiguration,
  IntakeReconciliationSummary,
  ComplianceStatus,
} from '../types/approval';
import {
  AlertTriangle,
  FileCheck,
  Plus,
  Edit3,
  Layers,
  CheckCircle2,
  Clock,
  RefreshCw,
  Info,
} from 'lucide-react';

export const AdmissionIntakeDashboard: React.FC = () => {
  const [configurations, setConfigurations] = useState<ApprovalConfiguration[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'matrix' | 'verification'>('matrix');

  // Amendment Modal state
  const [amendModalOpen, setAmendModalOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<ApprovalConfiguration | null>(null);
  const [amendIntake, setAmendIntake] = useState<number>(60);
  const [amendReference, setAmendReference] = useState<string>('');
  const [amendReason, setAmendReason] = useState<string>('');
  const [amendLoading, setAmendLoading] = useState(false);
  const [amendError, setAmendError] = useState<string | null>(null);

  // New Configuration Modal state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [programmes, setProgrammes] = useState<any[]>([]);
  const [newProgrammeId, setNewProgrammeId] = useState<string>('');
  const [newAcademicYear, setNewAcademicYear] = useState<string>('2024-25');
  const [newApprovedIntake, setNewApprovedIntake] = useState<number>(60);
  const [newRef, setNewRef] = useState<string>('AICTE/EOA/2024/001');
  const [newIssuingAuth, setNewIssuingAuth] = useState<string>('AICTE');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Allocations Drawer / Modal
  const [viewAllocModalOpen, setViewAllocModalOpen] = useState(false);
  const [activeAllocConfig, setActiveAllocConfig] = useState<ApprovalConfiguration | null>(null);

  // Verification State
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string>('');
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<IntakeReconciliationSummary | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  const fetchConfigurations = async () => {
    setLoading(true);
    try {
      const res = await api.get('/approvals/configurations');
      setConfigurations(res.data || []);
    } catch (err) {
      console.error('Failed to load approval configurations', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchProgrammesAndSnapshots = async () => {
    try {
      const pRes = await api.get('/institutions/programmes');
      setProgrammes(pRes.data || []);
      if (pRes.data && pRes.data.length > 0) {
        setNewProgrammeId(pRes.data[0].id);
      }

      const sRes = await api.get('/snapshots');
      setSnapshots(sRes.data || []);
      if (sRes.data && sRes.data.length > 0) {
        setSelectedSnapshotId(sRes.data[0].id);
      }
    } catch (err) {
      console.error('Failed to load auxiliary data', err);
    }
  };

  useEffect(() => {
    fetchConfigurations();
    fetchProgrammesAndSnapshots();
  }, []);

  const handleAmendSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedConfig) return;
    if (amendReason.trim().length < 10) {
      setAmendError('Amendment reason must be at least 10 characters.');
      return;
    }
    setAmendLoading(true);
    setAmendError(null);
    try {
      await api.post(`/approvals/configurations/${selectedConfig.id}/amend`, {
        approved_intake: amendIntake,
        approval_reference: amendReference || selectedConfig.approval_reference,
        amendment_reason: amendReason.trim(),
      });
      setAmendModalOpen(false);
      setSelectedConfig(null);
      setAmendReason('');
      fetchConfigurations();
    } catch (err: any) {
      setAmendError(extractErrorMessage(err, 'Failed to submit regulatory amendment.'));
    } finally {
      setAmendLoading(false);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    setCreateError(null);
    try {
      // Find programme to get institution_id
      const prog = programmes.find((p) => p.id === newProgrammeId);
      const instId = prog?.institution_id;
      if (!instId) {
        setCreateError('Could not determine institution ID for selected programme.');
        setCreateLoading(false);
        return;
      }

      await api.post('/approvals/configurations', {
        institution_id: instId,
        programme_id: newProgrammeId,
        academic_year: newAcademicYear,
        approved_intake: newApprovedIntake,
        approval_reference: newRef,
        issuing_authority: newIssuingAuth,
        effective_from: '2024-06-01',
        effective_to: '2025-05-31',
        supernumerary_quota_percentage: 15.0,
        lateral_entry_quota_percentage: 10.0,
        category_allocations: [
          {
            category_code: 'TFW',
            entry_level: 'FIRST_YEAR',
            allocation_type: 'ADDITIONAL_SUPERNUMERARY',
            allocation_basis: 'PERCENTAGE',
            allocated_value: 5.0,
            rounding_method: 'FLOOR',
            denominator_basis: 'SANCTIONED_INTAKE',
            policy_clause: 'AICTE APH 2024-25 Clause 4.1',
          },
          {
            category_code: 'MANAGEMENT_QUOTA',
            entry_level: 'FIRST_YEAR',
            allocation_type: 'WITHIN_SANCTIONED_INTAKE',
            allocation_basis: 'PERCENTAGE',
            allocated_value: 15.0,
            rounding_method: 'FLOOR',
            denominator_basis: 'SANCTIONED_INTAKE',
            policy_clause: 'AICTE APH 2024-25 Clause 2.3',
          },
        ],
      });
      setCreateModalOpen(false);
      fetchConfigurations();
    } catch (err: any) {
      setCreateError(extractErrorMessage(err, 'Failed to create approval configuration.'));
    } finally {
      setCreateLoading(false);
    }
  };

  const handleVerifyIntake = async () => {
    if (!selectedSnapshotId) return;
    setVerifying(true);
    setVerificationError(null);
    setVerificationResult(null);
    try {
      const res = await api.post('/approvals/intake/verify', {
        candidate_snapshot_id: selectedSnapshotId,
      });
      setVerificationResult(res.data);
    } catch (err: any) {
      setVerificationError(extractErrorMessage(err, 'Verification execution failed.'));
    } finally {
      setVerifying(false);
    }
  };

  const getStatusBadge = (status: ComplianceStatus) => {
    switch (status) {
      case 'COMPLIANT':
        return (
          <span className="gov-badge gov-badge-verified">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1 inline" /> COMPLIANT
          </span>
        );
      case 'EXCEPTION_FOUND':
        return (
          <span className="gov-badge gov-badge-danger">
            <AlertTriangle className="w-3.5 h-3.5 mr-1 inline" /> EXCEPTION FOUND
          </span>
        );
      case 'INSUFFICIENT_INFORMATION':
        return (
          <span className="gov-badge gov-badge-warning">
            <Info className="w-3.5 h-3.5 mr-1 inline" /> INSUFFICIENT INFO
          </span>
        );
      case 'PARTIALLY_EVALUATED':
        return (
          <span className="gov-badge gov-badge-info">
            <Clock className="w-3.5 h-3.5 mr-1 inline" /> PARTIALLY EVALUATED
          </span>
        );
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[#D7DEE5]">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                AICTE Statutory Approval & Intake Matrix
              </span>
              <span className="text-[11px] text-[#5F6B76] font-mono">Module 8 — Capacity & Quota Compliance</span>
            </div>
            <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
              Regulatory Intake & Quota Verification Engine / प्रवेश क्षमता एवं कोटा सत्यापन
            </h1>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Verifies reported student cohorts against statutory AICTE Extension of Approval (EoA) letters,
              versioned category quotas, and anti-double-counting invariants.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => {
                fetchConfigurations();
                fetchProgrammesAndSnapshots();
              }}
              className="gov-btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
              title="Refresh configurations"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => setCreateModalOpen(true)}
              className="gov-btn-primary text-xs py-2 px-4 flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Register Approval (EoA)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#D7DEE5] bg-white rounded-t px-2 pt-2">
        <button
          onClick={() => setActiveTab('matrix')}
          className={`py-2.5 px-5 font-bold text-xs uppercase tracking-wider border-b-2 flex items-center gap-2 transition ${
            activeTab === 'matrix'
              ? 'border-[#12345A] text-[#12345A]'
              : 'border-transparent text-[#5F6B76] hover:text-[#12345A]'
          }`}
        >
          <Layers className="w-3.5 h-3.5" /> Statutory Approval Matrix ({configurations.length})
        </button>
        <button
          onClick={() => setActiveTab('verification')}
          className={`py-2.5 px-5 font-bold text-xs uppercase tracking-wider border-b-2 flex items-center gap-2 transition ${
            activeTab === 'verification'
              ? 'border-[#12345A] text-[#12345A]'
              : 'border-transparent text-[#5F6B76] hover:text-[#12345A]'
          }`}
        >
          <FileCheck className="w-3.5 h-3.5" /> Intake Reconciliation & Compliance
        </button>
      </div>

      {/* Tab 1: Approval Matrix */}
      {activeTab === 'matrix' && (
        <div className="gov-table-container">
          <table className="gov-table w-full">
            <thead>
              <tr>
                <th>Academic Year</th>
                <th>Authority & Reference</th>
                <th>Version</th>
                <th>Approved Regular Intake</th>
                <th>Supernumerary / Lateral Quota</th>
                <th>Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-[#5F6B76]">
                    Loading statutory approval configurations...
                  </td>
                </tr>
              ) : configurations.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-[#5F6B76]">
                    No approval configurations found. Click "Register Approval (EoA)" to configure.
                  </td>
                </tr>
              ) : (
                configurations.map((cfg) => (
                  <tr key={cfg.id}>
                    <td className="font-semibold text-[#12345A]">
                      {cfg.academic_year}
                    </td>
                    <td>
                      <div className="font-semibold text-[#12345A]">{cfg.issuing_authority}</div>
                      <div className="text-[11px] text-[#5F6B76] font-mono">{cfg.approval_reference}</div>
                    </td>
                    <td>
                      <span className="gov-badge gov-badge-neutral font-mono">
                        v{cfg.configuration_version}
                      </span>
                    </td>
                    <td>
                      <span className="font-bold text-[#12345A] text-sm font-mono">{cfg.approved_intake}</span>{' '}
                      <span className="text-[11px] text-[#5F6B76]">seats</span>
                    </td>
                    <td className="text-xs space-y-0.5">
                      <div>Supernumerary: <strong className="text-[#12345A]">{cfg.supernumerary_quota_percentage}%</strong></div>
                      <div>Lateral Entry: <strong className="text-[#12345A]">{cfg.lateral_entry_quota_percentage}%</strong></div>
                    </td>
                    <td>
                      <span
                        className={`gov-badge ${
                          cfg.status === 'ACTIVE'
                            ? 'gov-badge-verified'
                            : cfg.status === 'SUPERSEDED'
                            ? 'gov-badge-neutral'
                            : 'gov-badge-danger'
                        }`}
                      >
                        {cfg.status}
                      </span>
                    </td>
                    <td className="text-right space-x-2">
                      <button
                        onClick={() => {
                          setActiveAllocConfig(cfg);
                          setViewAllocModalOpen(true);
                        }}
                        className="gov-btn-secondary text-xs py-1 px-2.5"
                      >
                        View Matrix
                      </button>
                      {cfg.status === 'ACTIVE' && (
                        <button
                          onClick={() => {
                            setSelectedConfig(cfg);
                            setAmendIntake(cfg.approved_intake);
                            setAmendReference(cfg.approval_reference);
                            setAmendModalOpen(true);
                          }}
                          className="gov-btn-secondary text-xs py-1 px-2.5 text-[#174F82]"
                        >
                          <Edit3 className="w-3 h-3 inline mr-1" /> Amend
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: Verification */}
      {activeTab === 'verification' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="bg-white p-5 rounded border border-[#D7DEE5] shadow-sm flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                Select Candidate Snapshot for Intake Verification
              </label>
              <select
                value={selectedSnapshotId}
                onChange={(e) => setSelectedSnapshotId(e.target.value)}
                className="gov-input text-xs w-full"
              >
                {snapshots.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.academic_year} — Snapshot #{s.id.slice(0, 8)} ({s.observed_headcount} students, {s.lifecycle_status})
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleVerifyIntake}
              disabled={verifying || !selectedSnapshotId}
              className="gov-btn-primary text-xs py-2 px-5 flex items-center gap-2 h-9"
            >
              {verifying ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileCheck className="w-3.5 h-3.5" />}
              {verifying ? 'Verifying Cohort...' : 'Execute Intake Reconciliation'}
            </button>
          </div>

          {verificationError && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-700" />
              <span>{typeof verificationError === 'string' ? verificationError : JSON.stringify(verificationError)}</span>
            </div>
          )}

          {/* Results Display */}
          {verificationResult && (
            <div className="space-y-6">
              {/* Overall Status Banner */}
              <div className="bg-white p-5 rounded border border-[#D7DEE5] shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                  <div className="text-[10px] uppercase font-bold text-[#5F6B76] tracking-wider">
                    Reconciliation Status
                  </div>
                  <div className="mt-1 flex items-center gap-3">
                    {getStatusBadge(verificationResult.compliance_status)}
                    <span className="text-xs text-[#5F6B76] font-mono">
                      Run #{verificationResult.reconciliation_run_id.slice(0, 8)}
                    </span>
                  </div>
                </div>

                <div className="flex gap-6 border-t md:border-t-0 pt-3 md:pt-0">
                  <div className="text-right">
                    <div className="text-[10px] font-bold text-[#5F6B76] uppercase">Regular Sanctioned</div>
                    <div className="font-bold text-[#12345A] text-lg font-mono">
                      {verificationResult.regular_enrolled_count} / {verificationResult.regular_approved_intake}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-bold text-[#5F6B76] uppercase">Supernumerary</div>
                    <div className="font-bold text-[#12345A] text-lg font-mono">
                      {verificationResult.supernumerary_enrolled_count} / {verificationResult.supernumerary_total_cap}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-bold text-[#5F6B76] uppercase">Lateral Entry</div>
                    <div className="font-bold text-[#12345A] text-lg font-mono">
                      {verificationResult.lateral_entry_enrolled_count} / {verificationResult.lateral_entry_approved_cap ?? 'N/A'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Category Matrix Results */}
              <div className="gov-table-container">
                <div className="p-3 border-b border-[#D7DEE5] bg-[#F4F6F8] font-bold text-xs uppercase text-[#12345A] flex items-center justify-between">
                  <span>Quota Category Utilization Breakdown</span>
                  <span className="text-[11px] text-[#5F6B76] font-normal">Unclassified Count: {verificationResult.unclassified_count}</span>
                </div>
                <table className="gov-table w-full">
                  <thead>
                    <tr>
                      <th>Category Code</th>
                      <th>Entry Level</th>
                      <th>Allocation Type</th>
                      <th>Approved Cap</th>
                      <th>Enrolled</th>
                      <th>Variance</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {verificationResult.category_breakdown.map((cat, idx) => (
                      <tr key={idx}>
                        <td className="font-bold text-[#12345A]">{cat.category_code}</td>
                        <td className="text-xs font-mono">{cat.entry_level}</td>
                        <td className="text-xs text-[#5F6B76]">{cat.allocation_type}</td>
                        <td className="font-mono">{cat.approved_limit ?? '—'}</td>
                        <td className="font-mono font-bold text-[#12345A]">{cat.observed_count}</td>
                        <td className="font-mono font-bold">
                          {cat.variance !== undefined && cat.variance !== null ? (
                            <span className={cat.variance > 0 ? 'text-[#C0392B]' : 'text-[#23834A]'}>
                              {cat.variance > 0 ? `+${cat.variance}` : cat.variance}
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>
                          <span
                            className={`gov-badge ${
                              cat.status === 'COMPLIANT'
                                ? 'gov-badge-verified'
                                : cat.status === 'EXCEPTION_FOUND'
                                ? 'gov-badge-danger'
                                : 'gov-badge-warning'
                            }`}
                          >
                            {cat.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Created Discrepancy Findings */}
              {verificationResult.discrepancy_cases_created.length > 0 && (
                <div className="bg-[#FFF8E7] rounded border border-[#FDE68A] p-5 space-y-3">
                  <div className="flex items-center gap-2 text-[#8F6B00] font-bold text-sm uppercase tracking-wide">
                    <AlertTriangle className="w-4 h-4 text-[#C0392B]" />
                    <span>Programme-Level Discrepancy Findings Generated ({verificationResult.discrepancy_cases_created.length})</span>
                  </div>
                  <p className="text-xs text-[#8F6B00]">
                    In compliance with regulatory standards, collective intake excesses generate programme-level cases without
                    attaching individual violator flags to student identities.
                  </p>
                  <div className="space-y-2">
                    {verificationResult.discrepancy_cases_created.map((c) => (
                      <div
                        key={c.case_id}
                        className="bg-white p-3 rounded border border-[#CBD7E3] flex items-center justify-between text-xs shadow-xs"
                      >
                        <div>
                          <span className="font-mono font-bold text-[#12345A]">{c.case_number}</span>
                          <span className="mx-2 text-[#8C9BA8]">•</span>
                          <span className="font-semibold text-[#C0392B]">{c.classification}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="gov-badge gov-badge-danger">
                            Priority: {c.review_priority}
                          </span>
                          <span className="gov-badge gov-badge-neutral font-mono">
                            Scope: {c.scope_type}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* View Matrix Allocations Modal */}
      {viewAllocModalOpen && activeAllocConfig && (
        <div className="fixed inset-0 bg-[#0F172A]/60 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded border border-[#CBD7E3] max-w-2xl w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#D7DEE5] pb-3">
              <div>
                <h3 className="font-bold text-[#12345A] text-base uppercase tracking-wide">Category Allocation Matrix</h3>
                <p className="text-xs text-[#5F6B76]">
                  {activeAllocConfig.academic_year} — Version {activeAllocConfig.configuration_version} ({activeAllocConfig.issuing_authority})
                </p>
              </div>
              <button
                onClick={() => setViewAllocModalOpen(false)}
                className="text-[#5F6B76] hover:text-[#12345A] font-bold text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 bg-[#F4F6F8] p-3 rounded border border-[#D7DEE5] text-xs">
                <div>
                  <span className="text-[#5F6B76]">Regular Sanctioned Intake:</span>{' '}
                  <span className="font-bold text-[#12345A] font-mono">{activeAllocConfig.approved_intake} seats</span>
                </div>
                <div>
                  <span className="text-[#5F6B76]">Reference:</span>{' '}
                  <span className="font-mono text-[#174F82]">{activeAllocConfig.approval_reference}</span>
                </div>
              </div>

              <div className="gov-table-container">
                <table className="gov-table w-full text-xs">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Type</th>
                      <th>Value</th>
                      <th>Rounding</th>
                      <th>Calculated Cap</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeAllocConfig.category_allocations?.map((a, i) => (
                      <tr key={i}>
                        <td className="font-bold text-[#12345A]">{a.category_code}</td>
                        <td className="text-[#5F6B76]">{a.allocation_type}</td>
                        <td className="font-mono">{a.allocated_value}%</td>
                        <td className="font-mono text-[#5F6B76]">{a.rounding_method}</td>
                        <td className="font-bold text-[#174F82] font-mono">{a.calculated_seat_cap ?? 'Auto'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-[#D7DEE5]">
              <button
                onClick={() => setViewAllocModalOpen(false)}
                className="gov-btn-secondary text-xs py-1.5 px-4"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Amend Approval Modal */}
      {amendModalOpen && selectedConfig && (
        <div className="fixed inset-0 bg-[#0F172A]/60 flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleAmendSubmit}
            className="bg-white rounded border border-[#CBD7E3] max-w-lg w-full p-5 space-y-4 shadow-xl"
          >
            <div className="border-b border-[#D7DEE5] pb-3">
              <h3 className="font-bold text-[#12345A] text-base uppercase tracking-wide">
                Regulatory Amendment (Version Transition)
              </h3>
              <p className="text-xs text-[#5F6B76]">
                Amending intake creates Version {selectedConfig.configuration_version + 1} and archives Version {selectedConfig.configuration_version}.
              </p>
            </div>

            {amendError && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-900 rounded text-xs">
                {amendError}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Amended Approved Intake
                </label>
                <input
                  type="number"
                  min={1}
                  value={amendIntake}
                  onChange={(e) => setAmendIntake(Number(e.target.value))}
                  className="gov-input font-mono text-xs w-full"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Revised EoA Reference
                </label>
                <input
                  type="text"
                  value={amendReference}
                  onChange={(e) => setAmendReference(e.target.value)}
                  placeholder={selectedConfig.approval_reference}
                  className="gov-input font-mono text-xs w-full"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Mandatory Statutory Justification Reason
                </label>
                <textarea
                  value={amendReason}
                  onChange={(e) => setAmendReason(e.target.value)}
                  placeholder="Detail statutory grounds (e.g. AICTE Appeal Committee Order #...)"
                  className="gov-input text-xs w-full"
                  rows={3}
                  required
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-[#D7DEE5]">
              <button
                type="button"
                onClick={() => setAmendModalOpen(false)}
                className="gov-btn-secondary text-xs py-1.5 px-3"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={amendLoading}
                className="gov-btn-primary text-xs py-1.5 px-4"
              >
                {amendLoading ? 'Submitting Amendment...' : 'Submit Versioned Amendment'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Register Approval Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 bg-[#0F172A]/60 flex items-center justify-center p-4 z-50">
          <form
            onSubmit={handleCreateSubmit}
            className="bg-white rounded border border-[#CBD7E3] max-w-lg w-full p-5 space-y-4 shadow-xl"
          >
            <div className="border-b border-[#D7DEE5] pb-3">
              <h3 className="font-bold text-[#12345A] text-base uppercase tracking-wide">
                Register Statutory Approval (EoA) / अनुमोदन पंजीकरण
              </h3>
              <p className="text-xs text-[#5F6B76]">
                Initializes Version 1 with statutory category quotas (TFW, Management Quota, Lateral Entry).
              </p>
            </div>

            {createError && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-900 rounded text-xs">
                {typeof createError === 'string' ? createError : JSON.stringify(createError)}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">Programme</label>
                <select
                  value={newProgrammeId}
                  onChange={(e) => setNewProgrammeId(e.target.value)}
                  className="gov-input text-xs w-full"
                >
                  {programmes.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.programme_name} ({p.degree_level})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">Academic Year</label>
                  <input
                    type="text"
                    value={newAcademicYear}
                    onChange={(e) => setNewAcademicYear(e.target.value)}
                    className="gov-input text-xs w-full"
                    placeholder="2024-25"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">Approved Intake</label>
                  <input
                    type="number"
                    min={1}
                    value={newApprovedIntake}
                    onChange={(e) => setNewApprovedIntake(Number(e.target.value))}
                    className="gov-input font-mono text-xs w-full"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Approval Reference / EoA Number
                </label>
                <input
                  type="text"
                  value={newRef}
                  onChange={(e) => setNewRef(e.target.value)}
                  className="gov-input font-mono text-xs w-full"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">Issuing Authority</label>
                <input
                  type="text"
                  value={newIssuingAuth}
                  onChange={(e) => setNewIssuingAuth(e.target.value)}
                  className="gov-input text-xs w-full"
                  required
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-[#D7DEE5]">
              <button
                type="button"
                onClick={() => setCreateModalOpen(false)}
                className="gov-btn-secondary text-xs py-1.5 px-3"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createLoading}
                className="gov-btn-primary text-xs py-1.5 px-4"
              >
                {createLoading ? 'Registering...' : 'Register Approval'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
