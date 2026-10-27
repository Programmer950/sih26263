import React, { useState } from 'react';
import { Lock, RefreshCw } from 'lucide-react';

export const ReportingIntegrity: React.FC = () => {
  const [replayState, setReplayState] = useState<'normal' | 'replayed'>('normal');

  return (
    <section id="reporting-integrity" className="section" style={{ backgroundColor: 'var(--bg-canvas)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3rem' }}>
          <span className="eyebrow">
            <Lock size={14} color="var(--ink-muted)" />
            DATA INTEGRITY GUARANTEE
          </span>
          <h2 className="section-title">
            A finding must never make a reported admission disappear.
          </h2>
          <p className="section-subtitle">
            Reported admissions are committed independently of unresolved identity or policy findings. Corrections create explicit reversals and new contributions, allowing counts to be reconstructed from the ledger.
          </p>
        </div>

        {/* Compact Illustrative Scenario Container */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-medium)',
            borderRadius: '12px',
            padding: '2rem',
            boxShadow: 'var(--shadow-sm)',
            marginBottom: '3rem',
          }}
        >
          {/* Header of Scenario */}
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem' }}>
            <div>
              <span className="eyebrow" style={{ color: 'var(--ink-primary)' }}>
                ILLUSTRATIVE CONCURRENCY & LEDGER SCENARIO
              </span>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.25rem' }}>
                Concurrent Intake vs. Sanctioned Program Capacity
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <span className="badge badge-neutral">SYNTHETIC SCENARIO</span>
              <span className="badge badge-blueprint">IDEMPOTENCY TEST</span>
            </div>
          </div>

          {/* Interactive Steps Visual */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '1.25rem',
              marginBottom: '2rem',
            }}
          >
            {/* Step 1: Initial State */}
            <div
              style={{
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '1.25rem',
              }}
            >
              <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--ink-muted)', marginBottom: '0.5rem' }}>
                STAGE 01: INITIAL BASELINE
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--ink-primary)', marginBottom: '0.25rem' }}>
                119 Admitted
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)' }}>
                Sanctioned Intake Capacity: <strong>120 seats</strong>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', marginTop: '0.5rem' }}>
                1 seat legally remaining before threshold breach.
              </div>
            </div>

            {/* Step 2: Concurrent Admission Arrival */}
            <div
              style={{
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '1.25rem',
              }}
            >
              <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--ink-muted)', marginBottom: '0.5rem' }}>
                STAGE 02: CONCURRENT INTAKE
              </div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--state-info-text)', marginBottom: '0.25rem' }}>
                +2 Admission Records
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)' }}>
                Admission #120 & #121 submit simultaneously across regional portals.
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--state-info-text)', marginTop: '0.5rem' }}>
                Both committed with ACID transactional guarantee.
              </div>
            </div>

            {/* Step 3: Resulting Ledger Count & Finding */}
            <div
              style={{
                backgroundColor: 'var(--state-pending-bg)',
                border: '1px solid var(--state-pending-border)',
                borderRadius: '8px',
                padding: '1.25rem',
              }}
            >
              <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--state-pending-text)', marginBottom: '0.5rem' }}>
                STAGE 03: RESULTING LEDGER
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--ink-primary)', marginBottom: '0.25rem' }}>
                121 Accounted For
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)' }}>
                1 Capacity Finding flagged: <strong>Over-sanctioned (+1)</strong>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--state-pending-text)', marginTop: '0.5rem', fontWeight: 500 }}>
                Crucial: Neither admission was silently dropped or rejected at ingestion!
              </div>
            </div>
          </div>

          {/* Idempotent Replay Verification Control */}
          <div
            style={{
              padding: '1.25rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-subtle)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
            }}
          >
            <div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                Idempotency Invariant: Repeated Report Replay
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)' }}>
                {replayState === 'replayed'
                  ? 'Replayed Admission #120 network packet again: Deterministic token matched. Count strictly unchanged at 121.'
                  : 'Test replaying one of the duplicate ingestion payloads to test ledger consistency.'}
              </div>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setReplayState(replayState === 'normal' ? 'replayed' : 'normal')}
            >
              <RefreshCw size={14} />
              <span>{replayState === 'normal' ? 'Replay Network Submission #120' : 'Reset Replay Test'}</span>
            </button>
          </div>

          <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--ink-muted)', fontStyle: 'italic', textAlign: 'right' }}>
            Illustrative scenario · Not measured production performance
          </div>
        </div>

        {/* 4 Implementation Mechanisms */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span className="badge badge-neutral">01</span>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                Deterministic Idempotency
              </h3>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              Client-generated idempotency keys ensure network retries, portal resubmissions, or dual uploads never double-count an enrolment in the journal.
            </p>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span className="badge badge-neutral">02</span>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                Transactional Constraints
              </h3>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              PostgreSQL serializable isolation and unique composite indices prevent race conditions during peak admission reporting windows across autonomous colleges.
            </p>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span className="badge badge-neutral">03</span>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                Durable Transactional Outbox
              </h3>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              Admission records and their downstream reconciliation tasks commit in a single database transaction, guaranteeing background workers resume cleanly after worker restarts.
            </p>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span className="badge badge-neutral">04</span>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                Version-Aware Processing
              </h3>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              Optimistic concurrency tokens prevent delayed or out-of-order events from overwriting newer institutional corrections or authorized reviewer waivers.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
