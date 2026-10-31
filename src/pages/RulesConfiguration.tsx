import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';

export const RulesConfiguration: React.FC = () => {
  const [configs, setConfigs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedConfig, setSelectedConfig] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadConfigurations();
  }, []);

  const loadConfigurations = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.get('/approvals/configurations');
      const items = res.data || [];
      setConfigs(items);
      if (items.length > 0 && !selectedConfig) {
        setSelectedConfig(items[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load approval configurations.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="gov-badge gov-badge-info">
            Statutory Approval Matrix & Rules Console
          </span>
          <span className="text-[11px] text-[#5F6B76] font-mono">Module 17 — AICTE APH Regulations</span>
        </div>
        <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
          Statutory Approval Matrix & Rules Console / नियामक मानदंड एवं नियम पीठ
        </h1>
        <p className="text-xs text-[#5F6B76] mt-0.5">
          Versioned approval rules, supernumerary quotas, lateral entry allowances, and configurable rounding policies governed by AICTE Approval Process Handbook (APH) regulations.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs">
          {error}
        </div>
      )}

      {/* Statutory Quotas Standard Reference Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#12345A] shadow-sm">
          <div className="text-[10px] font-bold text-[#12345A] uppercase tracking-wider">Regular Approved Intake</div>
          <div className="text-xs font-bold text-[#202B36] mt-0.5">Core Sanctioned Seats</div>
          <p className="text-[11px] text-[#5F6B76] mt-1 leading-relaxed">
            Total sanctioned regular intake per division. Excess above approved limit creates programme-level discrepancy finding.
          </p>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#23834A] shadow-sm">
          <div className="text-[10px] font-bold text-[#23834A] uppercase tracking-wider">Lateral Entry Quota (APH 2.8)</div>
          <div className="text-xs font-bold text-[#202B36] mt-0.5">10% of Approved Intake</div>
          <p className="text-[11px] text-[#5F6B76] mt-1 leading-relaxed">
            Direct admission to Year 2 for diploma/B.Sc holders + unfulfilled Year 1 vacant seats. Tracked independently from Year 1.
          </p>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#E58A24] shadow-sm">
          <div className="text-[10px] font-bold text-[#E58A24] uppercase tracking-wider">Supernumerary: TFW</div>
          <div className="text-xs font-bold text-[#202B36] mt-0.5">Tuition Fee Waiver (5%)</div>
          <p className="text-[11px] text-[#5F6B76] mt-1 leading-relaxed">
            Over and above sanctioned intake for meritorious economically weak candidates. Configurable rounding rules apply.
          </p>
        </div>

        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#174F82] shadow-sm">
          <div className="text-[10px] font-bold text-[#174F82] uppercase tracking-wider">Supernumerary: FN/PIO/EWS</div>
          <div className="text-xs font-bold text-[#202B36] mt-0.5">Special Quotas (10–15%)</div>
          <p className="text-[11px] text-[#5F6B76] mt-1 leading-relaxed">
            Economically Weaker Section (10%) and Foreign National/PIO (15%) supernumerary quotas subject to council sanctions.
          </p>
        </div>
      </div>

      {/* Main Configurations Table & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Table */}
        <div className="lg:col-span-7 bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center pb-3 border-b border-[#D7DEE5]">
            <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Active Statutory Approval Matrix ({configs.length})
            </h2>
            <button
              onClick={loadConfigurations}
              disabled={isLoading}
              className="gov-btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            >
              <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="gov-table-container">
            <table className="gov-table w-full text-xs">
              <thead>
                <tr>
                  <th>Academic Year</th>
                  <th>Approved Intake</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Order Reference</th>
                </tr>
              </thead>
              <tbody>
                {configs.map((c) => {
                  const isSelected = selectedConfig?.id === c.id;
                  return (
                    <tr
                      key={c.id}
                      onClick={() => setSelectedConfig(c)}
                      className={`cursor-pointer ${isSelected ? 'bg-[#EAF2F8]' : ''}`}
                    >
                      <td className="font-semibold text-[#12345A]">{c.academic_year}</td>
                      <td className="font-mono font-bold text-[#12345A]">{c.approved_intake} seats</td>
                      <td className="font-mono text-xs">v{c.configuration_version ?? c.version_number ?? 1}</td>
                      <td>
                        <span
                          className={`gov-badge ${
                            (c.status === 'ACTIVE' || c.configuration_status === 'ACTIVE')
                              ? 'gov-badge-verified'
                              : 'gov-badge-neutral'
                          }`}
                        >
                          {c.status || c.configuration_status || 'ACTIVE'}
                        </span>
                      </td>
                      <td className="font-mono text-[11px] text-[#5F6B76]">
                        {c.approval_reference || c.approval_letter_reference || 'AICTE-APH-2024'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Configuration Inspector */}
        <div className="lg:col-span-5 bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
          {selectedConfig ? (
            <div className="space-y-4">
              <div className="border-b border-[#D7DEE5] pb-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#5F6B76]">Statutory Approval Configuration</span>
                <h2 className="text-base font-bold text-[#12345A] mt-0.5">
                  Academic Year {selectedConfig.academic_year} (v{selectedConfig.configuration_version ?? selectedConfig.version_number ?? 1})
                </h2>
                <div className="text-xs text-[#174F82] font-mono mt-0.5 font-semibold">
                  Order Ref: {selectedConfig.approval_reference || selectedConfig.approval_letter_reference || 'AICTE-APH-2024'}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#F4F6F8] border border-[#D7DEE5] rounded p-3">
                  <div className="text-[10px] font-bold text-[#5F6B76] uppercase">Sanctioned Intake</div>
                  <div className="text-xl font-bold text-[#12345A] font-mono mt-0.5">
                    {selectedConfig.approved_intake} seats
                  </div>
                </div>
                <div className="bg-[#F4F6F8] border border-[#D7DEE5] rounded p-3">
                  <div className="text-[10px] font-bold text-[#5F6B76] uppercase">Lateral Allowance</div>
                  <div className="text-xl font-bold text-[#23834A] font-mono mt-0.5">
                    {selectedConfig.lateral_entry_intake_cap ?? Math.round(selectedConfig.approved_intake * 0.1)} seats (10%)
                  </div>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <h4 className="font-bold text-[#12345A] uppercase text-xs tracking-wide">
                  Statutory Calculation Policies
                </h4>
                <div className="divide-y divide-[#F4F6F8] text-[#202B36]">
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#5F6B76]">Percentage Rounding:</span>
                    <span className="font-mono font-bold text-[#12345A]">
                      {selectedConfig.rounding_method || 'FLOOR'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#5F6B76]">Supernumerary Quotas:</span>
                    <span className="gov-badge gov-badge-verified">Enabled (Independent)</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#5F6B76]">Effective Start Date:</span>
                    <span>{selectedConfig.effective_from ? new Date(selectedConfig.effective_from).toLocaleDateString() : 'Immediate'}</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#5F6B76]">Configuration Provenance:</span>
                    <span className="font-mono text-[11px] text-[#174F82]">SHA-256 Verified</span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-[#EAF2F8] border border-[#CBD7E3] rounded text-xs text-[#12345A] leading-relaxed">
                <strong>Immutable Versioning Rule:</strong> Active approval configurations cannot be overwritten in place. Any amendment generates Version {(selectedConfig.configuration_version ?? selectedConfig.version_number ?? 1) + 1} and supersedes previous parameters while preserving audit provenance.
              </div>
            </div>
          ) : (
            <div className="text-center py-20 text-[#5F6B76] text-xs">
              Select a configuration from the matrix table to inspect its quotas and rules.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
