import React from 'react';
import { Info } from 'lucide-react';

export const GovFooter: React.FC = () => {
  return (
    <footer
      style={{
        background: '#0B1F36',
        color: '#E2E8F0',
        fontSize: '12px',
        borderTop: '3px solid #174F82',
        padding: '24px 32px 16px',
        marginTop: 'auto',
      }}
    >
      <div
        style={{
          maxWidth: '1400px',
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '24px',
          paddingBottom: '20px',
          borderBottom: '1px solid #1E293B',
        }}
      >
        {/* Column 1: Platform Identity */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <img
              src="/emblem.png"
              alt="State Emblem of India"
              style={{
                height: '38px',
                width: 'auto',
                objectFit: 'contain',
                filter: 'brightness(0) invert(1)',
                opacity: 0.9,
              }}
            />
            <div style={{ fontWeight: 800, fontSize: '14px', color: '#FFFFFF', letterSpacing: '-0.2px' }}>
              APAAR SETU
            </div>
          </div>
          <p style={{ color: '#94A3B8', fontSize: '11.5px', lineHeight: 1.6, margin: 0 }}>
            Longitudinal Student Data Integrity & Statutory Regulatory Verification Platform. Built to demonstrate automated cohort tracking, explainable cross-institutional reconciliation, and privacy-responsible credential verification.
          </p>
        </div>

        {/* Column 2: Governance & Guidelines */}
        <div>
          <div style={{ fontWeight: 700, fontSize: '13px', color: '#E2E8F0', marginBottom: '8px' }}>
            Governance & Compliance Architecture
          </div>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '5px', fontSize: '11.5px', color: '#94A3B8' }}>
            <li>&bull; AICTE Approval Process Handbook (APH) Calculation Logic</li>
            <li>&bull; Digital Personal Data Protection Act (DPDPA 2023) Field Redaction</li>
            <li>&bull; HMAC-SHA256 Blind Indexing for APAAR ID Trajectory Resolution</li>
            <li>&bull; Strict Multi-Tenant Jurisdiction & IDOR Isolation Safeguards</li>
          </ul>
        </div>

        {/* Column 3: Portal Policies & Technical Scope */}
        <div>
          <div style={{ fontWeight: 700, fontSize: '13px', color: '#E2E8F0', marginBottom: '8px' }}>
            Technical Environment & Policies
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', fontSize: '11.5px', color: '#38BDF8', marginBottom: '8px' }}>
            <span style={{ cursor: 'pointer' }}>Privacy Policy</span>
            <span>|</span>
            <span style={{ cursor: 'pointer' }}>Terms of Service</span>
            <span>|</span>
            <span style={{ cursor: 'pointer' }}>Hyperlinking Policy</span>
            <span>|</span>
            <span style={{ cursor: 'pointer' }}>Accessibility Statement</span>
            <span>|</span>
            <span style={{ cursor: 'pointer' }}>Helpdesk</span>
          </div>
          <div style={{ fontSize: '11px', color: '#64748B' }}>
            Platform Version: <strong>v2.0-SIH-Gov</strong> &bull; Engine: Deterministic Python 3.13 / PostgreSQL 18
          </div>
        </div>
      </div>

      {/* Mandatory Statutory Demonstration Disclaimer */}
      <div
        style={{
          maxWidth: '1400px',
          margin: '16px auto 0',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: '#152A4A',
          border: '1px solid #1E3A5F',
          padding: '8px 14px',
          borderRadius: '4px',
          fontSize: '11.5px',
          color: '#CBD5E1',
        }}
      >
        <Info size={16} color="#E58A24" style={{ flexShrink: 0 }} />
        <span>
          <strong style={{ color: '#FF9933' }}>Demonstration Prototype Disclaimer:</strong> This portal is a working demonstration prototype developed specifically for the Smart India Hackathon problem statement (SIH26263). It is not an officially operated, endorsed, or deployed public service of AICTE or the Ministry of Education.
        </span>
      </div>
    </footer>
  );
};
