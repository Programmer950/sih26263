import React from 'react';
import { ShieldCheck, EyeOff, FileText, Undo2, Lock, AlertCircle } from 'lucide-react';

export const PrivacyResponsibleVerification: React.FC = () => {
  const principles = [
    {
      title: 'Purpose-scoped access',
      desc: 'Institutions access strictly their own reported records; authorized regulatory reviewers receive access only within the bounds of an active verification inquiry.',
      icon: Lock,
    },
    {
      title: 'Minimal disclosure',
      desc: 'Verification workflows are architected to disclose only minimal cryptographic assertions rather than indiscriminately broadcasting complete demographic records.',
      icon: EyeOff,
    },
    {
      title: 'Explicit verification states',
      desc: 'Format validity, source cryptographic authenticity, and demographic consistency remain three distinct checks—never lumped into an opaque boolean.',
      icon: FileText,
    },
    {
      title: 'Reversible decisions',
      desc: 'All identity links and human reviewer findings preserve an append-only audit trail and can be formally amended or revoked through authorized administrative workflows.',
      icon: Undo2,
    },
  ];

  return (
    <section className="section" style={{ backgroundColor: 'var(--bg-canvas)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3rem' }}>
          <span className="eyebrow">
            <ShieldCheck size={14} color="var(--ink-muted)" />
            ETHICAL ARCHITECTURE & PRIVACY BY DESIGN
          </span>
          <h2 className="section-title">
            Identity assurance without automatic identity decisions.
          </h2>
          <p className="section-subtitle">
            Responsible education technology must safeguard constitutional privacy, prevent algorithmic disenfranchisement, and ensure every student record is handled with deliberate administrative care.
          </p>
        </div>

        {/* 4 Concise Principles Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '1.5rem',
            marginBottom: '3rem',
          }}
        >
          {principles.map((p, idx) => {
            const Icon = p.icon;
            return (
              <div
                key={idx}
                className="card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  borderTop: '2px solid var(--state-verified)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--state-verified-bg)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Icon size={16} color="var(--state-verified-text)" />
                  </div>
                  <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                    {p.title}
                  </h3>
                </div>
                <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6, flexGrow: 1 }}>
                  {p.desc}
                </p>
              </div>
            );
          })}
        </div>

        {/* Mandatory Integration Boundary Disclosure */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderRadius: '8px',
            backgroundColor: 'var(--bg-subtle)',
            border: '1px solid var(--border-medium)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '1rem',
          }}
        >
          <AlertCircle size={20} color="var(--ink-muted)" style={{ flexShrink: 0, marginTop: '0.15rem' }} />
          <div>
            <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.25rem' }}>
              Statutory Integration Boundary Notice
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              The planned verification flow uses prototype assertions and test keys. It is not an official AICTE credential or a claim of live APAAR, ABC, or DigiLocker integration. No live student data or production administrative keys are utilized.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
