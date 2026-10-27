import React from 'react';
import { Clock } from 'lucide-react';

export const ProjectStatusSection: React.FC = () => {
  const roadmapPhases = [
    {
      phase: 'Phase 01',
      title: 'Evidence-preserving intake and staged corrections',
      desc: 'Schema validation for raw institutional admissions and staging for versioned amendment requests.',
    },
    {
      phase: 'Phase 02',
      title: 'Idempotent reporting ledger and worker recovery',
      desc: 'PostgreSQL transactional outbox, concurrency constraints, and crash-resilient worker execution.',
    },
    {
      phase: 'Phase 03',
      title: 'Identity candidate review and reversible links',
      desc: 'Candidate multi-pass blocking, field difference vectors, and human-in-the-loop review queues.',
    },
    {
      phase: 'Phase 04',
      title: 'Versioned policy and evidence checks',
      desc: 'Declarative rule evaluation against specific gazetted handbooks with explicit insufficient-evidence handling.',
    },
    {
      phase: 'Phase 05',
      title: 'Reconciliation Proof Chain, replay and impact preview',
      desc: 'End-to-end dependency tracking, run reproducibility, and preview calculations before ledger commit.',
    },
    {
      phase: 'Phase 06',
      title: 'Dashboards, controlled verification and evaluation',
      desc: 'Statutory compliance summaries, held-out accuracy benchmarking, and administrative reporting exports.',
    },
  ];

  return (
    <section id="project-status" className="section" style={{ backgroundColor: 'var(--bg-surface)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <span className="eyebrow">
              <Clock size={14} color="var(--ink-muted)" />
              ENGINEERING ROADMAP & CURRENT STATUS
            </span>
            <span className="badge badge-pending">
              PROTOTYPE IN DEVELOPMENT
            </span>
          </div>

          <h2 className="section-title">
            Building the reconciliation workflow, one verified invariant at a time.
          </h2>

          <p className="section-subtitle">
            We are developing APAAR SETU around a bounded, testable workflow using synthetic institutional data. The priority is to establish correct reporting, explainable identity candidates, contextual policy findings, and reproducible reconciliation history before adding broader integrations.
          </p>
        </div>

        {/* Roadmap Display - Honest development phases */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.25rem',
            marginBottom: '3rem',
          }}
        >
          {roadmapPhases.map((phase) => (
            <div
              key={phase.phase}
              style={{
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: 'var(--ink-muted)',
                  marginBottom: '0.5rem',
                }}
              >
                {phase.phase}
              </div>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.5rem' }}>
                {phase.title}
              </h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.55, flexGrow: 1 }}>
                {phase.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Project Metadata Card */}
        <div
          style={{
            backgroundColor: 'var(--bg-canvas)',
            border: '1px solid var(--border-medium)',
            borderRadius: '10px',
            padding: '1.75rem 2rem',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1.5rem',
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1.5rem', flexGrow: 1 }}>
            <div>
              <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', textTransform: 'uppercase' }}>
                Event
              </div>
              <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.2rem' }}>
                Smart India Hackathon 2026
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', textTransform: 'uppercase' }}>
                Problem Statement
              </div>
              <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.2rem' }}>
                SIH26263
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', textTransform: 'uppercase' }}>
                Team Name
              </div>
              <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.2rem' }}>
                Code Zero
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', textTransform: 'uppercase' }}>
                Team ID
              </div>
              <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.2rem' }}>
                197410
              </div>
            </div>
          </div>
        </div>

        {/* Future Facing Statement */}
        <div
          style={{
            marginTop: '2rem',
            textAlign: 'center',
            fontSize: '0.875rem',
            color: 'var(--ink-muted)',
            fontStyle: 'italic',
          }}
        >
          The public project page will evolve as the interactive prototype becomes available.
        </div>
      </div>
    </section>
  );
};
