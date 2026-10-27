import React from 'react';
import { Cpu } from 'lucide-react';

export const ArchitectureSection: React.FC = () => {
  const stackItems = [
    { area: 'Frontend Interface', tech: 'Next.js 14, TypeScript, TanStack Table', role: 'Role-scoped institutional portals, inspection views, and reconciliation queues.' },
    { area: 'Backend API Service', tech: 'FastAPI & Pydantic v2', role: 'Strict schema validation, idempotency guards, and asynchronous job triggers.' },
    { area: 'System of Record', tech: 'PostgreSQL 16 with ACID transactions', role: 'Immutable reporting ledger, optimistic concurrency, and audit logs.' },
    { area: 'Persistence & Migrations', tech: 'SQLAlchemy 2.0 & Alembic', role: 'Version-controlled relational schema migrations and typed query bindings.' },
    { area: 'Background Processing', tech: 'Durable Transactional Outbox + Worker', role: 'Fault-tolerant job pickup, retry backoff, and idempotent event processing.' },
    { area: 'Matching Baseline', tech: 'Deterministic exact matching + trigram indexing', role: 'High-recall candidate generation with controlled, benchmarked scoring.' },
    { area: 'Testing & Verification', tech: 'pytest + testcontainers (real PostgreSQL)', role: 'Rigorous concurrency race condition and replay validation suite.' },
  ];

  return (
    <section id="architecture" className="section" style={{ backgroundColor: 'var(--bg-surface)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3rem' }}>
          <span className="eyebrow">
            <Cpu size={14} color="var(--ink-muted)" />
            SYSTEM ARCHITECTURE & SPECIFICATION
          </span>
          <h2 className="section-title">
            A deliberately simple foundation for reliable reconciliation.
          </h2>
          <p className="section-subtitle">
            Rather than relying on distributed microservice sprawl or fragile cloud queues, APAAR SETU builds upon a battle-tested relational core with a single transactional outbox.
          </p>
        </div>

        {/* Clean Architectural Flow Diagram */}
        <div
          style={{
            backgroundColor: '#0b132b',
            color: '#ffffff',
            borderRadius: '12px',
            border: '1px solid #1e293b',
            padding: '2.5rem 2rem',
            boxShadow: 'var(--shadow-lg)',
            marginBottom: '3rem',
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '2rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#2dd4bf' }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600, letterSpacing: '0.06em', color: '#94a3b8' }}>
                END-TO-END TRANSACTIONAL EXECUTION FLOW
              </span>
            </div>
            <span className="badge badge-dark">
              PROPOSED ARCHITECTURE · SPECIFICATION
            </span>
          </div>

          {/* Architecture Pipeline Flow Nodes */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              alignItems: 'stretch',
            }}
          >
            {/* Step 1 */}
            <div style={{ backgroundColor: '#152243', border: '1px solid #273760', borderRadius: '8px', padding: '1.25rem' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#38bdf8', marginBottom: '0.4rem' }}>
                CLIENT & AUTH LAYER
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
                Institution Officer
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.45 }}>
                Next.js / TypeScript with role-scoped institutional OIDC credentials.
              </p>
            </div>

            {/* Step 2 */}
            <div style={{ backgroundColor: '#152243', border: '1px solid #273760', borderRadius: '8px', padding: '1.25rem' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#38bdf8', marginBottom: '0.4rem' }}>
                API GATEWAY
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
                FastAPI Service
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.45 }}>
                Pydantic validation, idempotency guards, and private import ingestion.
              </p>
            </div>

            {/* Step 3 */}
            <div style={{ backgroundColor: '#152243', border: '1.5px solid #0d9488', borderRadius: '8px', padding: '1.25rem' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#2dd4bf', marginBottom: '0.4rem' }}>
                SYSTEM OF RECORD
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
                PostgreSQL & Outbox
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.45 }}>
                Atomic commitment of intake records + transactional outbox messages.
              </p>
            </div>

            {/* Step 4 */}
            <div style={{ backgroundColor: '#152243', border: '1px solid #273760', borderRadius: '8px', padding: '1.25rem' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#38bdf8', marginBottom: '0.4rem' }}>
                RECONCILIATION ENGINE
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
                Worker Process
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.45 }}>
                Pulls outbox tasks; runs versioned identity, policy & evidence checks.
              </p>
            </div>

            {/* Step 5 */}
            <div style={{ backgroundColor: '#152243', border: '1px solid #273760', borderRadius: '8px', padding: '1.25rem' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', color: '#38bdf8', marginBottom: '0.4rem' }}>
                OUTPUT & AUDIT
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
                Proof Chain & Views
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.45 }}>
                Reproducible findings, reversible queues, and statutory compliance dashboards.
              </p>
            </div>
          </div>

          {/* Subsystems Callout */}
          <div
            style={{
              marginTop: '1.75rem',
              padding: '1rem 1.25rem',
              backgroundColor: '#111a33',
              borderRadius: '6px',
              border: '1px solid #1e293b',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
              fontSize: '0.75rem',
              color: '#94a3b8',
            }}
          >
            <div>
              <strong style={{ color: '#ffffff' }}>Supporting Infrastructure: </strong>
              SQLAlchemy & Alembic migrations · Institution-scoped authorization (OIDC) · Structured audit logging · Isolated import storage.
            </div>
            <div style={{ fontStyle: 'italic', color: '#64748b' }}>
              Proposed architecture · Implementation and validation in progress
            </div>
          </div>
        </div>

        {/* Technology Stack Specification Table */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '10px',
            overflow: 'hidden',
          }}
        >
          <div style={{ padding: '1.25rem 1.5rem', backgroundColor: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-subtle)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
              Proposed Production Technology Stack
            </h3>
            <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)' }}>
              Derived from SIH26263 engineering specification · Pragmatic, high-reliability stack choices
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--ink-muted)' }}>
                  <th style={{ padding: '0.75rem 1.25rem', width: '25%', fontWeight: 600 }}>LAYER / DOMAIN</th>
                  <th style={{ padding: '0.75rem 1.25rem', width: '35%', fontWeight: 600 }}>TECHNOLOGY CHOICE</th>
                  <th style={{ padding: '0.75rem 1.25rem', width: '40%', fontWeight: 600 }}>ARCHITECTURAL RATIONALE</th>
                </tr>
              </thead>
              <tbody>
                {stackItems.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: idx !== stackItems.length - 1 ? '1px solid var(--border-faint)' : 'none' }}>
                    <td style={{ padding: '0.85rem 1.25rem', fontWeight: 600, color: 'var(--ink-primary)' }}>
                      {item.area}
                    </td>
                    <td style={{ padding: '0.85rem 1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--ink-secondary)' }}>
                      {item.tech}
                    </td>
                    <td style={{ padding: '0.85rem 1.25rem', color: 'var(--ink-muted)' }}>
                      {item.role}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
};
