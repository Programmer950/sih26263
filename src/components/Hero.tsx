import React from 'react';
import { ArrowDownRight, Layers, FileCheck2, ShieldAlert, GitCommit, Database, Eye } from 'lucide-react';

export const Hero: React.FC = () => {
  return (
    <section
      id="overview"
      style={{
        paddingTop: '3.5rem',
        paddingBottom: '4.5rem',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'linear-gradient(180deg, var(--bg-canvas) 0%, #f4f3ed 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div className="container">
        {/* Top Eyebrow & Badges */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="eyebrow">
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--state-info)' }} />
            SMART INDIA HACKATHON 2026 · SIH26263
          </span>
          <span className="badge badge-neutral">
            TEAM CODE ZERO · ID 197410
          </span>
          <span className="badge badge-pending">
            INTERACTIVE PROTOTYPE · IN DEVELOPMENT
          </span>
        </div>

        {/* Hero Title & Subheading */}
        <div style={{ maxWidth: '58rem' }}>
          <h1
            style={{
              fontSize: 'clamp(2.25rem, 4.5vw, 3.6rem)',
              fontWeight: 800,
              letterSpacing: '-0.03em',
              lineHeight: 1.12,
              color: 'var(--ink-primary)',
              marginBottom: '1.25rem',
            }}
          >
            Every admission accounted for.<br />
            <span style={{ color: 'var(--ink-secondary)' }}>Every decision traceable.</span>
          </h1>
          <p
            style={{
              fontSize: 'clamp(1.05rem, 2vw, 1.25rem)',
              lineHeight: 1.6,
              color: 'var(--ink-secondary)',
              marginBottom: '2rem',
              maxWidth: '48rem',
            }}
          >
            APAAR SETU is designed to reconcile post-admission student records across institutions, investigate uncertain identity matches, and evaluate policy conflicts while preserving accurate enrolment reporting and the evidence behind every decision.
          </p>

          {/* Action CTAs */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', marginBottom: '3.5rem' }}>
            <a href="#four-layer-model" className="btn btn-primary" style={{ padding: '0.8rem 1.6rem', fontSize: '0.95rem' }}>
              <Layers size={18} />
              <span>Explore the reconciliation model</span>
            </a>
            <a href="#project-status" className="btn btn-secondary" style={{ padding: '0.8rem 1.4rem', fontSize: '0.95rem' }}>
              <span>View development status</span>
              <ArrowDownRight size={17} />
            </a>
          </div>
        </div>

        {/* Hero System Visualization: Cross-Institutional Record Reconciliation */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-medium)',
            borderRadius: '12px',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.05)',
            overflow: 'hidden',
          }}
        >
          {/* Header Bar of Diagram */}
          <div
            style={{
              padding: '0.875rem 1.25rem',
              borderBottom: '1px solid var(--border-subtle)',
              backgroundColor: '#fbfbfa',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--state-verified)' }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-secondary)' }}>
                CROSS-INSTITUTION RECONCILIATION INVARIANT FLOW
              </span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <span className="badge badge-neutral" style={{ fontSize: '0.65rem' }}>
                ILLUSTRATIVE SYSTEM MODEL
              </span>
              <span className="badge badge-blueprint" style={{ fontSize: '0.65rem' }}>
                SYNTHETIC DATA
              </span>
            </div>
          </div>

          {/* Visual Canvas */}
          <div style={{ padding: '1.75rem 1.5rem', backgroundColor: '#fdfdfc' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '1.5rem',
                position: 'relative',
              }}
            >
              {/* Institution A Source */}
              <div
                style={{
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-surface)',
                  padding: '1.25rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Database size={15} color="var(--ink-muted)" />
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--ink-primary)' }}>
                      Source Institution A
                    </span>
                  </div>
                  <span className="badge badge-neutral">Apex Tech Institute</span>
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', marginBottom: '0.85rem' }}>
                  Reported Admission Episode #2024-APX-8102
                </div>

                <div
                  style={{
                    backgroundColor: 'var(--bg-subtle)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.75rem',
                    lineHeight: 1.6,
                    color: 'var(--ink-secondary)',
                  }}
                >
                  <div><span style={{ color: 'var(--ink-muted)' }}>Name:</span> Rohan S. Sharma</div>
                  <div><span style={{ color: 'var(--ink-muted)' }}>DoB:</span> 2004-06-15</div>
                  <div><span style={{ color: 'var(--ink-muted)' }}>Programme:</span> B.Tech Computer Science</div>
                  <div><span style={{ color: 'var(--ink-muted)' }}>Status:</span> Enrolled (Active Batch)</div>
                  <div><span style={{ color: 'var(--ink-muted)' }}>APAAR Key:</span> ASSERTION_PROVISIONAL_901</div>
                </div>

                <div style={{ marginTop: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                    <FileCheck2 size={12} />
                    Reported Invariant: Committed
                  </span>
                </div>
              </div>

              {/* Institution B Source */}
              <div
                style={{
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-surface)',
                  padding: '1.25rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Database size={15} color="var(--ink-muted)" />
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--ink-primary)' }}>
                      Source Institution B
                    </span>
                  </div>
                  <span className="badge badge-neutral">Metropolitan Univ</span>
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', marginBottom: '0.85rem' }}>
                  Reported Admission Episode #2024-MTU-4190
                </div>

                <div
                  style={{
                    backgroundColor: 'var(--bg-subtle)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.75rem',
                    lineHeight: 1.6,
                    color: 'var(--ink-secondary)',
                  }}
                >
                  <div><span style={{ color: 'var(--ink-muted)' }}>Name:</span> Rohan Sharma</div>
                  <div><span style={{ color: 'var(--ink-muted)' }}>DoB:</span> 2004-06-18 (Discrepancy: +3 days)</div>
                  <div><span style={{ color: 'var(--ink-muted)' }}>Programme:</span> B.Tech Information Tech</div>
                  <div><span style={{ color: 'var(--ink-muted)' }}>Status:</span> Enrolled (Active Batch)</div>
                  <div><span style={{ color: 'var(--ink-muted)' }}>APAAR Key:</span> ASSERTION_PROVISIONAL_744</div>
                </div>

                <div style={{ marginTop: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                    <FileCheck2 size={12} />
                    Reported Invariant: Committed
                  </span>
                </div>
              </div>

              {/* Reconciliation & Identity Determination Node */}
              <div
                style={{
                  border: '1px solid var(--state-pending-border)',
                  backgroundColor: 'var(--state-pending-bg)',
                  borderRadius: '8px',
                  padding: '1.25rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Eye size={16} color="var(--state-pending)" />
                      <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--ink-primary)' }}>
                        Reconciliation Review Gate
                      </span>
                    </div>
                    <span className="badge badge-pending">Requires Review</span>
                  </div>

                  <div style={{ fontSize: '0.75rem', color: 'var(--ink-secondary)', marginBottom: '0.75rem', lineHeight: 1.5 }}>
                    Probable candidate match identified via secondary roll correlation, but birthdate discrepancy prevents automatic linkage.
                  </div>

                  <div
                    style={{
                      padding: '0.6rem 0.75rem',
                      borderRadius: '6px',
                      backgroundColor: 'rgba(255,255,255,0.7)',
                      border: '1px solid var(--state-pending-border)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.7125rem',
                      color: 'var(--state-pending-text)',
                      marginBottom: '0.5rem',
                    }}
                  >
                    <strong>Candidate match ≠ confirmed identity</strong>
                    <div style={{ marginTop: '0.2rem', color: 'var(--ink-secondary)' }}>
                      Decision reserved for authorized human verification. No automatic record merge.
                    </div>
                  </div>
                </div>

                <div style={{ paddingTop: '0.75rem', borderTop: '1px solid var(--state-pending-border)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <GitCommit size={14} color="var(--ink-muted)" />
                  <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-secondary)' }}>
                    Proof Chain Run: #RC-2026-SYN-001
                  </span>
                </div>
              </div>
            </div>

            {/* Bottom Invariant Banner */}
            <div
              style={{
                marginTop: '1.5rem',
                padding: '0.875rem 1.25rem',
                borderRadius: '8px',
                backgroundColor: 'var(--bg-dark)',
                color: 'var(--ink-inverted)',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ display: 'flex', padding: '0.35rem', borderRadius: '4px', backgroundColor: 'rgba(13, 148, 136, 0.2)' }}>
                  <ShieldAlert size={18} color="#2dd4bf" />
                </span>
                <div>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 600 }}>
                    Core System Invariant: Reported enrolment remains accounted for
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--ink-inverted-muted)' }}>
                    Both institutions retain their reported count of 1 admission each (Total: 2). Uncertainty does not erase records.
                  </div>
                </div>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#94a3b8' }}>
                Ledger Status: <span style={{ color: '#2dd4bf', fontWeight: 600 }}>Uncompromised</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
