import React, { useState } from 'react';
import { Shield, AlertTriangle, HelpCircle, CheckCircle2, Upload } from 'lucide-react';

export const PolicyAwareReconciliation: React.FC = () => {
  // State for timetable evidence attachment
  const [hasTimetableEvidence, setHasTimetableEvidence] = useState<boolean>(false);

  return (
    <section className="section" style={{ backgroundColor: 'var(--bg-canvas)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3rem' }}>
          <span className="eyebrow">
            <Shield size={14} color="var(--ink-muted)" />
            POLICY EVALUATION ENGINE
          </span>
          <h2 className="section-title">
            Context first. Conclusions only when evidence supports them.
          </h2>
          <p className="section-subtitle">
            Policy determinations depend on applicable regulatory versions, program delivery modes, shift timetables, and documentary proofs. Incomplete evidence produces a request for clarification—never an automated accusation.
          </p>
        </div>

        {/* 3 Compact Semantic Policy States */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '1.25rem',
            marginBottom: '3rem',
          }}
        >
          <div
            style={{
              padding: '1.25rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-surface)',
              border: '1.5px solid var(--state-error-border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span className="badge badge-error">POSSIBLE CONFLICT</span>
              <AlertTriangle size={16} color="var(--state-error-text)" />
            </div>
            <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.25rem' }}>
              Condition Requiring Review
            </div>
            <p style={{ fontSize: '0.78125rem', color: 'var(--ink-secondary)', lineHeight: 1.5 }}>
              Evidence indicates an explicit incompatibility against the applicable rule version (e.g. concurrent full-time day-shift degrees in physically distant locations).
            </p>
          </div>

          <div
            style={{
              padding: '1.25rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-surface)',
              border: '1.5px solid var(--state-pending-border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span className="badge badge-pending">INSUFFICIENT EVIDENCE</span>
              <HelpCircle size={16} color="var(--state-pending-text)" />
            </div>
            <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.25rem' }}>
              Missing Prerequisite Fact
            </div>
            <p style={{ fontSize: '0.78125rem', color: 'var(--ink-secondary)', lineHeight: 1.5 }}>
              A required factual document—such as a migration approval, attendance timetable, or distance mode affidavit—is pending submission. No punitive determination.
            </p>
          </div>

          <div
            style={{
              padding: '1.25rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-surface)',
              border: '1.5px solid var(--border-medium)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span className="badge badge-neutral">NOT APPLICABLE</span>
              <CheckCircle2 size={16} color="var(--ink-muted)" />
            </div>
            <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.25rem' }}>
              Outside Rule Scope
            </div>
            <p style={{ fontSize: '0.78125rem', color: 'var(--ink-secondary)', lineHeight: 1.5 }}>
              The regulatory clause applies only to specific degree categories, autonomous institutes, or post-2023 cohorts, and has no jurisdiction over this candidate.
            </p>
          </div>
        </div>

        {/* Fictional Dual-Programme Interactive Case Study */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-medium)',
            borderRadius: '12px',
            padding: '2rem',
            boxShadow: 'var(--shadow-sm)',
            marginBottom: '2rem',
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem' }}>
            <div>
              <span className="eyebrow" style={{ color: 'var(--ink-primary)' }}>
                ILLUSTRATIVE SCENARIO · DUAL ENROLMENT CONTEXT EVALUATION
              </span>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.25rem' }}>
                Simultaneous Programme Evaluation (Morning Degree + Evening Diploma)
              </div>
            </div>
            <span className="badge badge-neutral">SYNTHETIC REGULATORY BENCHMARK</span>
          </div>

          {/* Program Context Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '1.25rem',
              marginBottom: '1.75rem',
            }}
          >
            <div
              style={{
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '1.25rem',
              }}
            >
              <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', marginBottom: '0.25rem' }}>
                PROGRAMME RECORD 01
              </div>
              <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                B.Sc (Hons) Applied Physics
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', marginTop: '0.25rem' }}>
                Mode: Regular Full-Time · Shift: Morning (08:30 - 13:30)
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', marginTop: '0.5rem' }}>
                Institution: City Science College (Affiliated University)
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '1.25rem',
              }}
            >
              <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', marginBottom: '0.25rem' }}>
                PROGRAMME RECORD 02
              </div>
              <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                Postgraduate Diploma in Cyber Law
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', marginTop: '0.25rem' }}>
                Mode: Part-time / Continuing · Shift: Evening (18:00 - 21:00)
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', marginTop: '0.5rem' }}>
                Institution: National Law Academy (Autonomous)
              </div>
            </div>
          </div>

          {/* Interactive Evidence Attachment Simulation */}
          <div
            style={{
              padding: '1.25rem',
              borderRadius: '8px',
              backgroundColor: hasTimetableEvidence ? 'var(--state-verified-bg)' : 'var(--state-pending-bg)',
              border: `1px solid ${hasTimetableEvidence ? 'var(--state-verified-border)' : 'var(--state-pending-border)'}`,
              marginBottom: '1.5rem',
            }}
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                  EVIDENCE STATUS EVALUATION
                </div>
                <div
                  style={{
                    fontSize: '1rem',
                    fontWeight: 700,
                    color: hasTimetableEvidence ? 'var(--state-verified-text)' : 'var(--state-pending-text)',
                    marginTop: '0.2rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                >
                  {hasTimetableEvidence ? <CheckCircle2 size={18} /> : <HelpCircle size={18} />}
                  <span>
                    {hasTimetableEvidence
                      ? 'COMPLIANT EXCEPTION: Permissible Dual Enrolment'
                      : 'INSUFFICIENT EVIDENCE: Timetable Shift Proof Awaiting Upload'}
                  </span>
                </div>
              </div>

              <button
                type="button"
                className={`btn btn-sm ${hasTimetableEvidence ? 'btn-secondary' : 'btn-primary'}`}
                onClick={() => setHasTimetableEvidence(!hasTimetableEvidence)}
              >
                <Upload size={14} />
                <span>
                  {hasTimetableEvidence ? 'Remove Timetable Proof' : 'Attach Verified Shift Schedule Evidence'}
                </span>
              </button>
            </div>

            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.55 }}>
              {hasTimetableEvidence
                ? 'With verified shift documentation attached, the engine confirms non-overlapping instructional hours in accordance with versioned simultaneous degree guidelines. Only the dependent timetable check was reassessed; the reported enrolment records remained untouched throughout.'
                : 'Prior to timetable attachment, the engine refuses to issue a hasty "Fraud / Disqualification" verdict. It preserves the student’s admitted status while prompting the designated university desk for schedule verification.'}
            </p>
          </div>

          {/* Regulatory Disclaimer */}
          <div
            style={{
              padding: '0.85rem 1.25rem',
              borderRadius: '6px',
              backgroundColor: 'var(--bg-subtle)',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.75rem',
              color: 'var(--ink-muted)',
              lineHeight: 1.5,
            }}
          >
            <strong>Statutory Scope Notice:</strong> Normative rules must be reviewed against authoritative source clauses before activation. The scenario above illustrates a structured contextual rule engine design and does not represent an official universal AICTE or UGC regulatory determination.
          </div>
        </div>
      </div>
    </section>
  );
};
