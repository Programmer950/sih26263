import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  QrCode,
  CheckCircle,
} from 'lucide-react';
import { requestStudentVerification, verifyQrToken, QRVerificationResponse } from '../services/verification';
import { extractErrorMessage } from '../services/api';

interface CertificateSample {
  rollNo: string;
  name: string;
  apaarId: string;
  maskedApaar: string;
  programme: string;
  degree: string;
  division: string;
  issueDate: string;
  certRef: string;
}

const SAMPLE_CERTIFICATES: CertificateSample[] = [
  {
    rollNo: '23CSE001',
    name: 'Vikram Malhotra',
    apaarId: '984321098001',
    maskedApaar: 'XXXX-XXXX-8001',
    programme: 'Computer Science and Engineering',
    degree: 'Bachelor of Technology',
    division: 'First Class with Distinction',
    issueDate: 'May 20, 2026',
    certRef: 'AIT/2026/BTECH/CSE-001',
  },
  {
    rollNo: '23CSE002',
    name: 'Tanvi Shah',
    apaarId: '984321098002',
    maskedApaar: 'XXXX-XXXX-8002',
    programme: 'Computer Science and Engineering',
    degree: 'Bachelor of Technology',
    division: 'First Class with Distinction',
    issueDate: 'May 20, 2026',
    certRef: 'AIT/2026/BTECH/CSE-002',
  },
  {
    rollNo: '23CSE003',
    name: 'Aditya Verma',
    apaarId: '984321098003',
    maskedApaar: 'XXXX-XXXX-8003',
    programme: 'Computer Science and Engineering',
    degree: 'Bachelor of Technology',
    division: 'First Class',
    issueDate: 'May 20, 2026',
    certRef: 'AIT/2026/BTECH/CSE-003',
  },
];

export const CertificateViewer: React.FC = () => {
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const cert = SAMPLE_CERTIFICATES[selectedIdx];

  // Verification state
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<QRVerificationResponse | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [activeToken, setActiveToken] = useState<string>('');

  useEffect(() => {
    // Generate active verification token on cert switch
    initVerificationToken();
  }, [selectedIdx]);

  const initVerificationToken = async (): Promise<string | null> => {
    try {
      setVerificationResult(null);
      setVerificationError(null);
      const res = await requestStudentVerification({
        apaar_id: cert.apaarId,
        stated_purpose: 'Degree Certificate Authenticity Verification via Linked QR Code',
        consent_confirmed: true,
        organization_name: 'AICTE / Statutory Regulatory Verification Portal',
        verifier_name: 'Academic Verifier',
      });
      if (res.token) {
        setActiveToken(res.token);
        return res.token;
      }
      return null;
    } catch (err: any) {
      console.error('Failed to init cert token:', err);
      return null;
    }
  };

  const handleVerifyCredential = async () => {
    let token = activeToken;
    if (!token) {
      token = (await initVerificationToken()) || '';
    }
    if (!token) {
      setVerificationError('No valid verification token available for this credential.');
      return;
    }
    try {
      setIsVerifying(true);
      setVerificationError(null);
      const res = await verifyQrToken(token);
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationError(extractErrorMessage(err, 'Verification failed.'));
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#D7DEE5] gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                Module 13 — Verifiable Credentials
              </span>
              <span className="text-[11px] text-[#5F6B76] font-mono">ISO-18013-5 / W3C VC Compatible</span>
            </div>
            <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
              Institutional Certificate & QR Identity Linkage / प्रमाण-पत्र सत्यापन
            </h1>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Demonstrates institutional certificates presenting APAAR ID alongside institutional student ID with authenticable, privacy-preserving QR verification.
            </p>
          </div>

          {/* Certificate Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-[#12345A]">Select Student:</span>
            {SAMPLE_CERTIFICATES.map((c, i) => (
              <button
                key={c.rollNo}
                onClick={() => setSelectedIdx(i)}
                className={`px-3 py-1.5 text-xs font-mono font-bold rounded transition ${
                  selectedIdx === i
                    ? 'bg-[#12345A] text-white shadow-xs'
                    : 'bg-[#F4F6F8] text-[#202B36] border border-[#D7DEE5] hover:bg-[#EAF2F8]'
                }`}
              >
                {c.rollNo}
              </button>
            ))}
          </div>
        </div>

        {/* Synthetic Document Disclaimer */}
        <div className="mt-4 p-3 bg-[#EAF2F8] border border-[#CBD7E3] rounded text-xs text-[#12345A] flex items-center gap-2.5">
          <ShieldCheck size={18} className="text-[#174F82] shrink-0" />
          <div>
            <strong>Demonstration Document:</strong> This certificate illustrates how universities link verified APAAR references to degrees and transcripts. The QR code links directly to the APAAR SETU cryptographic verification endpoint with zero personal data leakage.
          </div>
        </div>
      </div>

      {/* Main Certificate Presentation Card */}
      <div className="bg-white border-4 border-double border-[#12345A] rounded p-8 md:p-12 shadow-md relative">
        {/* Certificate Watermark / Header */}
        <div className="text-center border-b border-[#CBD7E3] pb-6 mb-8">
          <div className="text-xs tracking-widest font-bold text-[#E58A24] uppercase mb-1">
            Autonomous Institution • Approved by AICTE
          </div>
          <h2 className="text-2xl md:text-3xl font-extrabold text-[#12345A] uppercase tracking-wider font-serif">
            APEX INSTITUTE OF TECHNOLOGY
          </h2>
          <div className="text-xs text-[#5F6B76] mt-1">
            Permanent AICTE Approval Reference: AICTE-APEX-ENG-2024 • Established under State Act
          </div>
        </div>

        {/* Certificate Body */}
        <div className="text-center max-w-2xl mx-auto space-y-4">
          <p className="text-sm text-[#5F6B76] italic">
            Upon the recommendation of the Academic Council, hereby confers upon
          </p>
          <div className="text-2xl md:text-3xl font-bold text-[#12345A] font-serif underline decoration-[#174F82] underline-offset-4">
            {cert.name}
          </div>
          <p className="text-sm text-[#5F6B76]">
            the degree of
          </p>
          <div className="text-xl md:text-2xl font-bold text-[#174F82] tracking-wide">
            {cert.degree}
          </div>
          <div className="text-base font-semibold text-[#202B36]">
            in {cert.programme}
          </div>
          <p className="text-xs md:text-sm text-[#5F6B76] leading-relaxed">
            having passed the prescribed examinations in the academic year <strong>2025-26</strong> and placed in the <strong>{cert.division}</strong>.
          </p>
        </div>

        {/* Dual Identifier and QR Section */}
        <div className="flex flex-col md:flex-row justify-between items-center md:items-end border-t border-[#CBD7E3] pt-6 mt-8 gap-6">
          {/* Identifiers */}
          <div className="text-xs text-[#202B36] space-y-1.5 text-center md:text-left">
            <div>
              <span className="text-[#5F6B76]">Institutional Roll No:</span> <span className="font-mono font-bold text-[#12345A]">{cert.rollNo}</span>
            </div>
            <div>
              <span className="text-[#5F6B76]">Masked APAAR ID:</span> <span className="font-mono font-bold text-[#174F82]">{cert.maskedApaar}</span>
            </div>
            <div>
              <span className="text-[#5F6B76]">Certificate Reference:</span> <span className="font-mono text-[#5F6B76]">{cert.certRef}</span>
            </div>
            <div>
              <span className="text-[#5F6B76]">Date of Issue:</span> <span className="text-[#202B36]">{cert.issueDate}</span>
            </div>
          </div>

          {/* Interactive QR Code Widget */}
          <div className="text-center">
            <div className="w-28 h-28 border-2 border-[#12345A] rounded p-2 bg-white flex flex-col items-center justify-center mx-auto mb-1.5 shadow-xs">
              <QrCode size={70} className="text-[#12345A]" />
              <div className="text-[8px] font-bold text-[#5F6B76] tracking-wider mt-1">
                SCAN TO VERIFY
              </div>
            </div>
            <div className="text-[10px] text-[#5F6B76] max-w-[150px]">
              Resolves to APAAR SETU Digital Attestation
            </div>
          </div>

          {/* Signatures */}
          <div className="text-center md:text-right text-xs text-[#202B36]">
            <div className="w-40 border-b border-[#8C9BA8] mb-1.5 h-9 flex items-end justify-center md:justify-end">
              <span className="font-serif italic text-base text-[#12345A]">Prof. S. R. Raman</span>
            </div>
            <div className="font-bold text-[#12345A]">Registrar</div>
            <div className="text-[#5F6B76] text-[11px]">Apex Institute of Technology</div>
          </div>
        </div>
      </div>

      {/* Live Verification Trigger & Output */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-[#D7DEE5] gap-3">
          <div>
            <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Live Digital Attestation & Verification Test / डिजिटल सत्यापन परीक्षण
            </h3>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Simulates an authorized verifier (employer, higher-education portal, or statutory body) inspecting the credential via the token endpoint.
            </p>
          </div>
          <button
            onClick={handleVerifyCredential}
            disabled={isVerifying}
            className="gov-btn-primary text-xs py-2 px-4 flex items-center gap-2"
          >
            <ShieldCheck size={14} />
            {isVerifying ? 'Verifying Token...' : 'Verify Certificate Authenticity'}
          </button>
        </div>

        {verificationError && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs">
            {typeof verificationError === 'string' ? verificationError : JSON.stringify(verificationError)}
          </div>
        )}

        {verificationResult && (
          <div className="bg-[#EAF7EE] border border-[#23834A] rounded p-4 space-y-3">
            <div className="flex items-center gap-2 text-[#166534] font-bold text-xs uppercase tracking-wide">
              <CheckCircle size={16} />
              <span>Attestation Status: {verificationResult.status}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-[#202B36]">
              <div><span className="text-[#5F6B76]">Student Name:</span> <strong>{verificationResult.disclosed_record?.student_name || cert.name}</strong></div>
              <div><span className="text-[#5F6B76]">Masked APAAR:</span> <strong className="font-mono text-[#174F82]">{verificationResult.disclosed_record?.masked_apaar || cert.maskedApaar}</strong></div>
              <div><span className="text-[#5F6B76]">Enrolled Institution:</span> <strong>{verificationResult.disclosed_record?.institution_name || 'Apex Institute of Technology'}</strong></div>
              <div><span className="text-[#5F6B76]">Academic Programme:</span> <strong>{verificationResult.disclosed_record?.programme_name || cert.programme}</strong></div>
              <div><span className="text-[#5F6B76]">Enrolment Status:</span> <strong className="gov-badge gov-badge-verified">{verificationResult.disclosed_record?.enrolment_status || 'ACTIVE_ON_ROLL'}</strong></div>
              <div><span className="text-[#5F6B76]">Verified At:</span> <strong>{new Date(verificationResult.verified_at || Date.now()).toLocaleString()}</strong></div>
            </div>

            <div className="pt-2 border-t border-[#BBF7D0] text-[11px] text-[#166534]">
              Cryptographically verified against the national student integrity registry via token <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-[#BBF7D0]">{activeToken.slice(0, 16)}...</code>. Zero raw identifiers disclosed.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
