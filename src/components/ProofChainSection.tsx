import React, { useState } from 'react';
import { GitCommit, GitBranch, RotateCcw, CheckCircle2, AlertCircle, ChevronRight, History } from 'lucide-react';

export const ProofChainSection: React.FC = () => {
  // Local state for simulation
  const [isCorrected, setIsCorrected] = useState<boolean>(false);
  const [selectedNode, setSelectedNode] = useState<number>(4);

  const nodes = [
    {
      id: 1,
      title: '1. Source Evidence Artifact',
      category: 'INPUT ARTIFACT',
      desc: 'Raw admission batch payload from Institution A & B with signed metadata.',
      detail: isCorrected
        ? 'Batch #2024-ADM-081 + Reviewer Addendum Doc #REV-DOC-992 (Attested School Leaving Certificate confirming separate parents).'
        : 'Batch #2024-ADM-081 (Apex Tech) & Batch #2024-ADM-419 (Metro Univ).',
      hash: isCorrected ? 'sha256:4a8b...199c' : 'sha256:9f2c...884a',
    },
    {
      id: 2,
      title: '2. Identity Assertion & Comparison',
      category: 'IDENTITY CANDIDATE',
      desc: 'Pairwise field similarity vector across candidate admissions.',
      detail: isCorrected
        ? 'Decision logged: SEPARATE_ENTITIES. Verified distinct parentage. Reversible human review by Nodal Officer ID #OFF-772.'
        : 'Score: 0.887. Names agree (Rohit Patil). DoB disagrees by 3 days. Status: UNVERIFIED_CANDIDATE.',
      hash: isCorrected ? 'assertion:sep_distinct_v2' : 'assertion:cand_unverified_v1',
    },
    {
      id: 3,
      title: '3. Applicable Approval & Rule Version',
      category: 'REGULATORY CONTEXT',
      desc: 'Specific gazetted handbook clauses active at the time of intake.',
      detail: 'Rule: REG-AICTE-DUAL-ENROL-V2024.1 (Clause 4.3 - Concurrent Full-Time Prohibition).',
      hash: 'rule_ast:sha256:d41d...c94b',
    },
    {
      id: 4,
      title: '4. Reconciliation Run Node',
      category: 'RUN LEDGER',
      desc: 'Deterministic evaluation execution binding inputs to statutory logic.',
      detail: isCorrected
        ? 'Active Run #1043 (Trigger: Reviewer Correction) → Evaluated in 42ms. Run #1042 archived in immutable audit sequence.'
        : 'Active Run #1042 (Trigger: Initial Batch Intake) → Output: Flagged for authorized review.',
      hash: isCorrected ? 'run:1043_parent_1042' : 'run:1042_parent_genesis',
    },
    {
      id: 5,
      title: '5. Finding & Reviewer Decision',
      category: 'FINDING JOURNAL',
      desc: 'Auditable finding record with explicit provenance chain.',
      detail: isCorrected
        ? 'Finding #F-8802 status updated to [RESOLVED_LEGITIMATE_SEPARATE]. Cause: Disproved candidate match. No duplicate.'
        : 'Finding #F-8802 flagged [SUSPECTED_DUAL_ENROLMENT]. Requires documentary verification. No automated penalty.',
      hash: isCorrected ? 'finding:f8802_state_resolved' : 'finding:f8802_state_open',
    },
    {
      id: 6,
      title: '6. Versioned Outcome & Resulting Count',
      category: 'REPORTING INTEGRITY',
      desc: 'Final ledger entry reflecting admitted seats without loss.',
      detail:
        'Apex Tech: 1 admission. Metro Univ: 1 admission. Total Reported: 2 admissions accounted for. 0 dropped.',
      hash: 'ledger_snapshot:v2024.final',
    },
  ];

  return (
    <section id="proof-chain" className="section" style={{ backgroundColor: '#f5f4ef' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3rem' }}>
          <span className="eyebrow">
            <GitBranch size={14} color="var(--ink-muted)" />
            CORE TECHNICAL CONTRIBUTION
          </span>
          <h2 className="section-title">
            Reconstruct every finding from the evidence that produced it.
          </h2>
          <p className="section-subtitle">
            Each reconciliation finding is linked to a recorded run containing the relevant source versions, identity decisions, applicable rule and approval versions, evidence dependencies, and resulting decision history.
          </p>
        </div>

        {/* 3-Step Mechanism Card */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: '1.25rem 1.5rem',
            marginBottom: '2.5rem',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-muted)' }}>
              CORE PIPELINE
            </span>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.85rem' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                fontWeight: 600,
                padding: '0.35rem 0.75rem',
                backgroundColor: 'var(--bg-subtle)',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
                color: 'var(--ink-primary)',
              }}
            >
              Record Inputs & Context
            </span>
            <ChevronRight size={16} color="var(--ink-muted)" />
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                fontWeight: 600,
                padding: '0.35rem 0.75rem',
                backgroundColor: 'var(--bg-subtle)',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
                color: 'var(--ink-primary)',
              }}
            >
              Versioned Reconciliation Run
            </span>
            <ChevronRight size={16} color="var(--ink-muted)" />
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                fontWeight: 600,
                padding: '0.35rem 0.75rem',
                backgroundColor: 'var(--bg-dark)',
                color: 'var(--ink-inverted)',
                borderRadius: '6px',
              }}
            >
              Reproducible Finding & Ledger Entry
            </span>
          </div>
        </div>

        {/* Interactive Simulation Container */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-medium)',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-md)',
            overflow: 'hidden',
            marginBottom: '3rem',
          }}
        >
          {/* Simulation Control Toolbar */}
          <div
            style={{
              padding: '1.25rem 1.5rem',
              backgroundColor: '#fafaf8',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <span className="badge badge-blueprint">PROOF CHAIN REPLAY SIMULATOR</span>
                <span className="badge badge-neutral">SYNTHETIC DATA</span>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--ink-muted)' }}>
                Demonstrating reversible human decisions, run versioning, and immutable reporting preservation.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <button
                type="button"
                onClick={() => setIsCorrected(!isCorrected)}
                className={`btn ${isCorrected ? 'btn-secondary' : 'btn-primary'}`}
                style={{ fontSize: '0.8125rem', padding: '0.5rem 1rem' }}
              >
                {isCorrected ? (
                  <>
                    <RotateCcw size={15} />
                    <span>Reset to Initial Conflict State</span>
                  </>
                ) : (
                  <>
                    <GitCommit size={15} />
                    <span>Simulate a Reviewer Correction</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Interactive Node Graph */}
          <div style={{ padding: '2rem 1.5rem' }}>
            {/* Simulation Status Overview */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: '1rem',
                marginBottom: '2rem',
                padding: '1rem',
                borderRadius: '8px',
                backgroundColor: isCorrected ? 'var(--state-verified-bg)' : 'var(--state-pending-bg)',
                border: `1px solid ${isCorrected ? 'var(--state-verified-border)' : 'var(--state-pending-border)'}`,
              }}
            >
              <div>
                <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                  ACTIVE RECONCILIATION RUN
                </div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.2rem' }}>
                  {isCorrected ? 'Run #1043 (Correction Replay)' : 'Run #1042 (Initial Automated Scan)'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--ink-secondary)', marginTop: '0.25rem' }}>
                  {isCorrected
                    ? 'Trigger: Authorized reviewer submitted attested affidavit.'
                    : 'Trigger: Automated intake comparison batch.'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                  FINDING #F-8802 STATUS
                </div>
                <div
                  style={{
                    fontSize: '1.05rem',
                    fontWeight: 700,
                    color: isCorrected ? 'var(--state-verified-text)' : 'var(--state-pending-text)',
                    marginTop: '0.2rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                >
                  {isCorrected ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                  <span>{isCorrected ? 'RESOLVED (Distinct Persons)' : 'REQUIRES HUMAN REVIEW'}</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--ink-secondary)', marginTop: '0.25rem' }}>
                  {isCorrected ? 'Previous Run #1042 preserved in audit trail.' : 'No punitive action taken on student.'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                  REPORTED ADMISSIONS PRESERVED
                </div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--state-verified-text)', marginTop: '0.2rem' }}>
                  2 / 2 (100% Invariant Preserved)
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--ink-secondary)', marginTop: '0.25rem' }}>
                  Neither admission was erased or collapsed.
                </div>
              </div>
            </div>

            {/* Dependency Nodes Grid */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--ink-muted)', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Proof Chain Graph Nodes (Click to inspect node details)
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
                  gap: '0.85rem',
                }}
              >
                {nodes.map((node) => {
                  const isSelected = node.id === selectedNode;
                  return (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => setSelectedNode(node.id)}
                      style={{
                        padding: '1rem',
                        borderRadius: '8px',
                        border: `1.5px solid ${isSelected ? 'var(--ink-primary)' : 'var(--border-subtle)'}`,
                        backgroundColor: isSelected ? 'var(--bg-subtle)' : 'var(--bg-surface)',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all var(--transition-fast)',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        minHeight: '130px',
                      }}
                    >
                      <div>
                        <span
                          style={{
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.625rem',
                            fontWeight: 700,
                            color: isSelected ? 'var(--ink-primary)' : 'var(--ink-muted)',
                            display: 'block',
                            marginBottom: '0.35rem',
                          }}
                        >
                          {node.category}
                        </span>
                        <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--ink-primary)', lineHeight: 1.3 }}>
                          {node.title}
                        </div>
                      </div>

                      <div style={{ fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', marginTop: '0.75rem' }}>
                        Hash: {node.hash.substring(0, 16)}...
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Selected Node Detailed Inspector */}
            {selectedNode && (
              <div
                style={{
                  padding: '1.25rem',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-subtle)',
                  border: '1px solid var(--border-medium)',
                }}
              >
                {(() => {
                  const curr = nodes.find((n) => n.id === selectedNode) || nodes[0];
                  return (
                    <div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                          Node Inspector: {curr.title}
                        </span>
                        <span className="badge badge-neutral font-mono">
                          {curr.hash}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', marginBottom: '0.75rem' }}>
                        {curr.desc}
                      </p>
                      <div
                        style={{
                          padding: '0.75rem',
                          borderRadius: '6px',
                          backgroundColor: 'var(--bg-surface)',
                          border: '1px solid var(--border-faint)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.75rem',
                          lineHeight: 1.6,
                          color: 'var(--ink-primary)',
                        }}
                      >
                        <strong>Active State: </strong>
                        {curr.detail}
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>

          {/* Replay and Audit History Footer */}
          <div
            style={{
              padding: '1rem 1.5rem',
              backgroundColor: '#fafaf8',
              borderTop: '1px solid var(--border-subtle)',
              fontSize: '0.75rem',
              color: 'var(--ink-muted)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <History size={14} />
              <span>
                Immutable Audit Trail: <strong>{isCorrected ? '2 Runs Recorded' : '1 Run Recorded'}</strong>
              </span>
            </div>
            <span>
              Synthetic demonstration · Not connected to live production student records
            </span>
          </div>
        </div>

        {/* Technical Mechanism Explanation */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.5rem' }}>
              Structured Evidence Model
            </h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              The Proof Chain is not a claim of a new cryptographic invention. It is a rigorous data model built from versioned records, deterministic execution runs, and explicit dependency relationships that make findings mathematically reproducible.
            </p>
          </div>

          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.5rem' }}>
              Reversible Human Decisions
            </h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              When an authorized reviewer discovers that two candidates are separate individuals or confirms a transfer certificate, the change is recorded as a new run without destroying earlier findings, preserving an accountable institutional history.
            </p>
          </div>

          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.5rem' }}>
              Decoupled Impact Preview
            </h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              Reviewers can simulate the downstream impact of an identity link or policy waiver before committing it. The system calculates affected programme quotas and statutory limits prior to writing to the permanent ledger.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
