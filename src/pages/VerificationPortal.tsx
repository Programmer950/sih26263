import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  requestStudentVerification,
  verifyQrToken,
  VerificationRequestResponse,
  QRVerificationResponse,
} from '../services/verification';
import { extractErrorMessage } from '../services/api';

export const VerificationPortal: React.FC = () => {
  const { user } = useAuth();
  const [apaarId, setApaarId] = useState<string>('984321098001');
  const [statedPurpose, setStatedPurpose] = useState<string>(
    'Pre-employment educational background verification for employment candidate.'
  );
  const [consentConfirmed, setConsentConfirmed] = useState<boolean>(true);
  const [organizationName, setOrganizationName] = useState<string>('Tata Consultancy Services (TCS)');
  const [verifierName, setVerifierName] = useState<string>(user?.email || 'External Background Auditor');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationRequestResponse | null>(null);

  // QR Test Inspection State
  const [qrTokenInput, setQrTokenInput] = useState<string>('');
  const [qrInspectionResult, setQrInspectionResult] = useState<QRVerificationResponse | null>(null);
  const [isQrLoading, setIsQrLoading] = useState<boolean>(false);

  const handleSubmitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apaarId.trim() || !statedPurpose.trim()) {
      setError('Please provide APAAR reference and stated verification purpose.');
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const res = await requestStudentVerification({
        apaar_id: apaarId.trim(),
        stated_purpose: statedPurpose.trim(),
        consent_confirmed: consentConfirmed,
        organization_name: organizationName.trim(),
        verifier_name: verifierName.trim(),
      });
      setResult(res);
      if (res.token) {
        setQrTokenInput(res.token);
      }
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Verification request failed.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleInspectQrToken = async (tokenToVerify?: string) => {
    const t = tokenToVerify || qrTokenInput;
    if (!t.trim()) return;
    try {
      setIsQrLoading(true);
      const res = await verifyQrToken(t.trim());
      setQrInspectionResult(res);
    } catch (err: any) {
      setQrInspectionResult({
        valid: false,
        status: 'INVALID',
        reason: extractErrorMessage(err, 'Token validation failure'),
      });
    } finally {
      setIsQrLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="gov-badge gov-badge-info">
            Authorised Verification Gateway
          </span>
          <span className="text-[11px] text-[#5F6B76] font-mono">Workstream 4 — Minimal Disclosure</span>
        </div>
        <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
          Authorised Student Verification Portal / छात्र सत्यापन पोर्टल
        </h1>
        <p className="text-xs text-[#5F6B76] mt-0.5">
          Enables permitted employers and credential verifiers to request authenticated student status under explicit stated purpose and candidate consent.
        </p>

        {/* Simulated Integration Notice */}
        <div className="mt-4 p-3 bg-[#EAF2F8] border border-[#CBD7E3] rounded text-xs text-[#12345A] flex items-start gap-2.5">
          <span className="font-bold text-sm leading-none mt-0.5 text-[#174F82]">ℹ</span>
          <div>
            <span className="font-semibold">Statutory Demonstration Notice:</span> This prototype implements simulated authorization and verification workflows for AICTE SIH26263. It makes no claim of official live government API connectivity or statutory authority.
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Verification Request Form */}
        <div className="lg:col-span-7 bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
          <div className="border-b border-[#D7DEE5] pb-3">
            <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Initiate External Verification / सत्यापन अनुरोध प्रपत्र
            </h2>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Submit candidate's 12-digit reference with legally documented purpose and verified consent.
            </p>
          </div>

          <form onSubmit={handleSubmitRequest} className="space-y-4">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                APAAR ID / Student Reference <span className="text-red-600">*</span>
              </label>
              <input
                type="text"
                value={apaarId}
                onChange={(e) => setApaarId(e.target.value)}
                placeholder="12-digit numeric APAAR reference"
                className="gov-input font-mono text-xs w-full"
                required
              />
              <span className="text-[10px] text-[#5F6B76] mt-0.5 block">
                Candidate reference used for cryptographic blind-index resolution under DPDPA norms.
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Requesting Organisation
                </label>
                <input
                  type="text"
                  value={organizationName}
                  onChange={(e) => setOrganizationName(e.target.value)}
                  className="gov-input text-xs w-full"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Verifier Name / Official Email
                </label>
                <input
                  type="text"
                  value={verifierName}
                  onChange={(e) => setVerifierName(e.target.value)}
                  className="gov-input text-xs w-full"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                Mandatory Stated Purpose <span className="text-red-600">*</span>
              </label>
              <textarea
                rows={3}
                value={statedPurpose}
                onChange={(e) => setStatedPurpose(e.target.value)}
                placeholder="Explicitly describe the purpose of verification..."
                className="gov-input text-xs w-full"
                required
              />
              <span className="text-[10px] text-[#5F6B76] mt-0.5 block">
                Stated purpose is immutably recorded into the tamper-evident audit ledger.
              </span>
            </div>

            <div className="p-3 bg-[#F4F6F8] border border-[#D7DEE5] rounded flex items-start gap-2.5">
              <input
                type="checkbox"
                id="consentCheck"
                checked={consentConfirmed}
                onChange={(e) => setConsentConfirmed(e.target.checked)}
                className="mt-0.5 h-4 w-4 accent-[#12345A]"
              />
              <label htmlFor="consentCheck" className="text-xs text-[#202B36] leading-relaxed">
                <span className="font-bold text-[#12345A]">Candidate Consent Certified:</span> I certify that candidate consent has been documented for this background verification request in compliance with statutory data privacy principles.
              </label>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs">
                {typeof error === 'string' ? error : JSON.stringify(error)}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !consentConfirmed}
              className="gov-btn-primary text-xs py-2 px-5 w-full flex items-center justify-center gap-2"
            >
              {isLoading ? 'Verifying Student Identity...' : 'Submit Verification Request'}
            </button>
          </form>
        </div>

        {/* Right Column: Disclosure Result & QR Token Verification */}
        <div className="lg:col-span-5 space-y-6">
          {/* Result Card */}
          {result ? (
            <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#D7DEE5]">
                <div>
                  <span className="text-[10px] font-mono text-[#5F6B76] block">{result.verification_reference}</span>
                  <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">Verification Outcome</h3>
                </div>
                <span
                  className={`gov-badge ${result.status === 'VERIFIED'
                    ? 'gov-badge-verified'
                    : 'gov-badge-danger'
                    }`}
                >
                  {result.status}
                </span>
              </div>

              {result.disclosed_record ? (
                <div className="space-y-3">
                  <div className="p-3.5 bg-[#EAF7EE] border border-[#23834A] rounded space-y-1 text-xs text-[#202B36]">
                    <div className="font-bold text-[#12345A] text-sm">
                      {result.disclosed_record.student_name}
                    </div>
                    <div className="text-[#174F82] font-mono text-xs">
                      Masked APAAR: {result.disclosed_record.masked_apaar}
                    </div>
                    <div className="text-[#202B36] font-medium">
                      {result.disclosed_record.institution_name}
                    </div>
                    <div className="text-[#5F6B76]">
                      {result.disclosed_record.programme_name} ({result.disclosed_record.academic_year})
                    </div>
                    <div className="pt-2 flex items-center justify-between text-[11px] text-[#166534] border-t border-[#BBF7D0]">
                      <span>Status: <strong className="gov-badge gov-badge-verified">{result.disclosed_record.enrolment_status}</strong></span>
                      <span>Support: {result.disclosed_record.supported_status}</span>
                    </div>
                  </div>

                  {/* QR Token Card */}
                  <div className="p-3 bg-[#F4F6F8] border border-[#D7DEE5] rounded space-y-2 text-xs">
                    <span className="font-bold text-[#12345A] uppercase text-[10px]">Secure Verification Token</span>
                    <div className="p-2 bg-white border border-[#CBD7E3] rounded font-mono text-[11px] text-[#174F82] break-all">
                      {result.token}
                    </div>
                    <button
                      onClick={() => handleInspectQrToken(result.token)}
                      className="w-full gov-btn-secondary text-xs py-1.5"
                    >
                      Inspect via Public QR Endpoint →
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-6 text-center text-[#5F6B76] text-xs">
                  {result.message || 'No matching student records found for the requested reference.'}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white border border-[#D7DEE5] rounded p-8 text-center text-[#5F6B76] text-xs shadow-sm">
              <div className="w-10 h-10 bg-[#EAF2F8] text-[#12345A] rounded-full flex items-center justify-center mx-auto mb-2 font-bold text-base">
                📋
              </div>
              Submit a verification request to inspect authorized minimal disclosure findings.
            </div>
          )}

          {/* QR Resolution Inspector */}
          <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-3">
            <div className="border-b border-[#D7DEE5] pb-2">
              <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
                Public QR Attestation Inspector
              </h3>
              <p className="text-xs text-[#5F6B76] mt-0.5">
                Simulates scanning an authenticated QR token without requiring privileged login credentials.
              </p>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={qrTokenInput}
                onChange={(e) => setQrTokenInput(e.target.value)}
                placeholder="Paste verification token..."
                className="gov-input font-mono text-xs flex-1"
              />
              <button
                onClick={() => handleInspectQrToken()}
                disabled={isQrLoading || !qrTokenInput.trim()}
                className="gov-btn-primary text-xs py-2 px-4"
              >
                {isQrLoading ? 'Verifying...' : 'Resolve'}
              </button>
            </div>

            {qrInspectionResult && (
              <div
                className={`p-3 rounded border text-xs space-y-1.5 ${qrInspectionResult.valid
                  ? 'bg-[#EAF7EE] border-[#23834A] text-[#166534]'
                  : 'bg-red-50 border-red-200 text-red-900'
                  }`}
              >
                <div className="flex items-center justify-between font-bold">
                  <span>Status: {qrInspectionResult.status}</span>
                  <span className={`gov-badge ${qrInspectionResult.valid ? 'gov-badge-verified' : 'gov-badge-danger'}`}>
                    {qrInspectionResult.valid ? 'VALID TOKEN' : 'INVALID / EXPIRED'}
                  </span>
                </div>
                {qrInspectionResult.disclosed_record && (
                  <div className="pt-2 text-[11px] space-y-0.5 border-t border-[#BBF7D0]">
                    <div><span className="text-[#5F6B76]">Student:</span> <strong>{qrInspectionResult.disclosed_record.student_name}</strong></div>
                    <div><span className="text-[#5F6B76]">APAAR:</span> <strong className="font-mono text-[#174F82]">{qrInspectionResult.disclosed_record.masked_apaar}</strong></div>
                    <div><span className="text-[#5F6B76]">Institution:</span> <strong>{qrInspectionResult.disclosed_record.institution_name}</strong></div>
                  </div>
                )}
                {qrInspectionResult.reason && (
                  <div className="text-[11px] text-red-800">{qrInspectionResult.reason}</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
