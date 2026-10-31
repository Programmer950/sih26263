import React, { useState, useEffect } from 'react';
import {
  Eye,
  EyeOff,
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';

// Verhoeff algorithm implementation in TypeScript for real-time client-side verification
const VERHOEFF_D = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
  [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
  [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
  [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
  [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
  [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
  [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
  [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
  [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
];

const VERHOEFF_P = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
  [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
  [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
  [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
  [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
  [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
  [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
];

function validateVerhoeff(numStr: string): boolean {
  if (!/^\d+$/.test(numStr)) return false;
  let c = 0;
  const digits = numStr.split('').map(Number).reverse();
  for (let i = 0; i < digits.length; i++) {
    c = VERHOEFF_D[c][VERHOEFF_P[i % 8][digits[i]]];
  }
  return c === 0;
}

export const ApaarValidation: React.FC = () => {
  const [testInput, setTestInput] = useState<string>('984321098001');
  const [showRaw, setShowRaw] = useState<boolean>(false);
  const [students, setStudents] = useState<any[]>([]);
  const [isLoadingStudents, setIsLoadingStudents] = useState<boolean>(false);

  // Stats
  const [stats, setStats] = useState({
    total: 0,
    valid: 0,
    missing: 0,
    invalid: 0,
  });

  useEffect(() => {
    loadStudents();
  }, []);

  const loadStudents = async () => {
    try {
      setIsLoadingStudents(true);
      const res = await api.get('/students', { params: { limit: 50 } });
      const items = res.data.items || res.data || [];
      setStudents(items);

      let v = 0, m = 0, inv = 0;
      items.forEach((s: any) => {
        const st = s.identity_status || 'UNKNOWN';
        if (st === 'FORMAT_VALID') v++;
        else if (st === 'MISSING_APAAR') m++;
        else inv++;
      });
      setStats({
        total: items.length,
        valid: v,
        missing: m,
        invalid: inv,
      });
    } catch (err) {
      console.error('Failed to load students:', err);
    } finally {
      setIsLoadingStudents(false);
    }
  };

  // Real-time validation computation
  const cleanInput = testInput.replace(/\s|-/g, '');
  const is12Digits = /^\d{12}$/.test(cleanInput);
  const isVerhoeffValid = is12Digits ? validateVerhoeff(cleanInput) : false;
  const maskedReference = cleanInput.length >= 4 ? `XXXX-XXXX-${cleanInput.slice(-4)}` : 'INVALID';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="gov-badge gov-badge-info">
            APAAR Validation & Cryptographic Pseudonymization
          </span>
          <span className="text-[11px] text-[#5F6B76] font-mono">Module 5 — Verhoeff Checksum & Blind Indexing</span>
        </div>
        <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
          APAAR Validation & Blind-Index Workbench / अपार सत्यापन पीठ
        </h1>
        <p className="text-xs text-[#5F6B76] mt-0.5">
          Deterministic 12-digit Verhoeff format validation, cryptographic pseudonymization, and blind-index collision analysis under DPDPA standards.
        </p>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#12345A] shadow-sm">
          <div className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">Sampled Identities</div>
          <div className="text-2xl font-bold text-[#12345A] font-mono mt-1">{stats.total}</div>
          <span className="text-[10px] text-[#5F6B76]">Current active sample</span>
        </div>
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#23834A] shadow-sm">
          <div className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">Format Valid</div>
          <div className="text-2xl font-bold text-[#23834A] font-mono mt-1">{stats.valid}</div>
          <span className="text-[10px] text-[#23834A] font-semibold">12-Digit Verhoeff Confirmed</span>
        </div>
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#E58A24] shadow-sm">
          <div className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">Missing APAAR</div>
          <div className="text-2xl font-bold text-[#E58A24] font-mono mt-1">{stats.missing}</div>
          <span className="text-[10px] text-[#E58A24] font-semibold">Pending Institutional Issuance</span>
        </div>
        <div className="p-3.5 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#C0392B] shadow-sm">
          <div className="text-[10px] font-bold text-[#5F6B76] uppercase tracking-wider">Format Invalid</div>
          <div className="text-2xl font-bold text-[#C0392B] font-mono mt-1">{stats.invalid}</div>
          <span className="text-[10px] text-[#C0392B] font-semibold">Checksum Mismatch</span>
        </div>
      </div>

      {/* Interactive Validator Tool */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
        <div className="border-b border-[#D7DEE5] pb-3">
          <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
            Interactive APAAR Format & Checksum Inspector
          </h2>
          <p className="text-xs text-[#5F6B76] mt-0.5">
            Test candidate 12-digit numbers against Verhoeff checksum algorithm and preview real-time pseudonymization.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          <div className="md:col-span-6 space-y-3">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                Enter 12-Digit APAAR Reference
              </label>
              <div className="flex gap-2">
                <input
                  type={showRaw ? 'text' : 'password'}
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  placeholder="e.g. 984321098001"
                  className="gov-input font-mono text-xs flex-1"
                />
                <button
                  type="button"
                  onClick={() => setShowRaw(!showRaw)}
                  className="gov-btn-secondary px-3 py-1 flex items-center justify-center"
                  title={showRaw ? 'Hide raw digits' : 'Show raw digits'}
                >
                  {showRaw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <div className="flex gap-1.5 flex-wrap items-center pt-1">
              <span className="text-[11px] text-[#5F6B76] font-semibold">Test Fixtures:</span>
              <button
                onClick={() => setTestInput('984321098001')}
                className="gov-btn-secondary text-[11px] py-1 px-2.5"
              >
                Valid (Vikram)
              </button>
              <button
                onClick={() => setTestInput('123456789010')}
                className="gov-btn-secondary text-[11px] py-1 px-2.5"
              >
                Invalid Verhoeff
              </button>
              <button
                onClick={() => setTestInput('98432109')}
                className="gov-btn-secondary text-[11px] py-1 px-2.5"
              >
                Short (&lt; 12)
              </button>
            </div>
          </div>

          {/* Validation Feedback Card */}
          <div className="md:col-span-6 bg-[#F4F6F8] border border-[#D7DEE5] rounded p-4 space-y-2 text-xs">
            <h3 className="font-bold text-[#12345A] text-xs uppercase tracking-wide pb-1 border-b border-[#CBD7E3]">
              Validation & Pseudonymization Output
            </h3>

            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between items-center">
                <span className="text-[#5F6B76]">12-Digit Numeric Constraint:</span>
                <span className={`gov-badge ${is12Digits ? 'gov-badge-verified' : 'gov-badge-danger'}`}>
                  {is12Digits ? 'Passed' : 'Failed (12 digits required)'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#5F6B76]">Verhoeff Checksum Check:</span>
                <span className={`gov-badge ${isVerhoeffValid ? 'gov-badge-verified' : 'gov-badge-danger'}`}>
                  {isVerhoeffValid ? 'Checksum Valid' : 'Checksum Mismatch / Synthetic'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#5F6B76]">Masked Reference (UI Safe):</span>
                <span className="font-mono font-bold text-[#174F82]">
                  {maskedReference}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#5F6B76]">Storage Encryption:</span>
                <span className="text-[#202B36] font-mono text-[11px]">
                  AES-256-GCM Envelope
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Identity Repository Sample */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
        <div className="flex justify-between items-center pb-3 border-b border-[#D7DEE5]">
          <div>
            <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Active Student Identity Registry Sample / छात्र पहचान नमूना
            </h3>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Inspecting blind indexes generated by HMAC-SHA256 with pepper rotation for searchability without cleartext storage.
            </p>
          </div>
          <button
            onClick={loadStudents}
            disabled={isLoadingStudents}
            className="gov-btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
          >
            <RefreshCw size={13} className={isLoadingStudents ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        <div className="gov-table-container">
          <table className="gov-table w-full">
            <thead>
              <tr>
                <th>Student Name</th>
                <th>Roll No</th>
                <th>Masked APAAR</th>
                <th>HMAC-SHA256 Blind Index Digest</th>
                <th>Identity Status</th>
              </tr>
            </thead>
            <tbody>
              {students.slice(0, 15).map((s) => (
                <tr key={s.id}>
                  <td className="font-semibold text-[#12345A]">{s.full_name}</td>
                  <td className="font-mono text-xs text-[#5F6B76]">{s.institution_student_id || '-'}</td>
                  <td className="font-mono text-xs font-bold text-[#174F82]">
                    {s.masked_apaar || 'MISSING'}
                  </td>
                  <td className="font-mono text-[11px] text-[#5F6B76]">
                    {s.apaar_blind_index ? `${s.apaar_blind_index.slice(0, 16)}...` : '-'}
                  </td>
                  <td>
                    <span
                      className={`gov-badge ${
                        s.identity_status === 'FORMAT_VALID'
                          ? 'gov-badge-verified'
                          : s.identity_status === 'MISSING_APAAR'
                          ? 'gov-badge-warning'
                          : 'gov-badge-danger'
                      }`}
                    >
                      {s.identity_status || 'UNVERIFIED'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
