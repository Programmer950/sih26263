import React, { useState } from 'react';
import { Layers, ArrowRight } from 'lucide-react';

interface LayerData {
  id: number;
  layerName: string;
  question: string;
  badge: string;
  badgeType: 'verified' | 'pending' | 'blueprint' | 'neutral';
  shortDesc: string;
  deepDive: string;
  syntheticExample: {
    title: string;
    fields: { label: string; value: string; state?: 'verified' | 'pending' | 'neutral' }[];
    invariantNote: string;
  };
  keyMechanism: string;
}

export const FourLayerModel: React.FC = () => {
  const [activeLayer, setActiveLayer] = useState<number>(1);

  const layers: LayerData[] = [
    {
      id: 1,
      layerName: 'Layer 1: Reported Truth',
      question: 'What did the institution actually report?',
      badge: 'REPORTING INVARIANT',
      badgeType: 'verified',
      shortDesc: 'Represents raw admission episodes and reporting-ledger entries without downstream judgment.',
      deepDive:
        'When an authorized nodal officer submits an admission cohort, those records are committed to an append-only reporting ledger. Downstream findings, suspected duplicates, or disputed identifiers never silently delete, hide, or decrement reported enrolments. Corrections generate explicit reversal records and new versioned submissions.',
      syntheticExample: {
        title: 'Reported Admission Episode Ledger Record',
        fields: [
          { label: 'Event ID', value: 'TX-2024-ADM-08819', state: 'neutral' },
          { label: 'Reporting Entity', value: 'Govt. Engineering College, Jabalpur', state: 'neutral' },
          { label: 'Programme & Year', value: 'B.Tech Mechanical Engg (2024-2028 Cohort)', state: 'neutral' },
          { label: 'Submitted Seats', value: '60 / Sanctioned: 60', state: 'verified' },
          { label: 'Ledger State', value: 'Committed to Immutable Journal (Hash Verified)', state: 'verified' },
        ],
        invariantNote: 'Invariant: Even if student records within this cohort trigger policy inquiries, the count of 60 admitted students remains legally and statistically recorded.',
      },
      keyMechanism: 'Append-only ledger with deterministic transaction IDs and versioned snapshot tracking.',
    },
    {
      id: 2,
      layerName: 'Layer 2: Identity Confidence',
      question: 'Which records may refer to the same person?',
      badge: 'PROBABILISTIC & REVIEWABLE',
      badgeType: 'pending',
      shortDesc: 'Evaluates candidate matches, field-level similarity, and reversible human-reviewed links.',
      deepDive:
        'APAAR and local identifiers are treated as identity assertions with provenance, not blind database primary keys. Candidates are produced via deterministic and fuzzy matching pipelines. An identity link between two admissions is never automatically forged by an algorithm; it requires an explicit, reversible human reviewer determination.',
      syntheticExample: {
        title: 'Candidate Match Assertion Matrix',
        fields: [
          { label: 'Candidate Record 1', value: 'Devendra K. Verma (NIT Raipur - Civil)', state: 'neutral' },
          { label: 'Candidate Record 2', value: 'Devendra Kumar Verma (GEC Bilaspur - Civil)', state: 'neutral' },
          { label: 'Field Matches', value: 'Secondary Roll (Exact), DoB (+1 day mismatch)', state: 'pending' },
          { label: 'Similarity Score', value: '0.892 (High Candidate Threshold)', state: 'neutral' },
          { label: 'Identity Link State', value: 'UNVERIFIED_CANDIDATE (Requires Officer Review)', state: 'pending' },
        ],
        invariantNote: 'Invariant: Candidate match ≠ confirmed identity. Both admissions exist independently until an authorized reviewer records a reversible determination.',
      },
      keyMechanism: 'Exact indexing + tokenized trigram matching + human review audit trail.',
    },
    {
      id: 3,
      layerName: 'Layer 3: Policy Determination',
      question: 'Does the available evidence establish a policy violation?',
      badge: 'CONTEXTUAL RULES ENGINE',
      badgeType: 'blueprint',
      shortDesc: 'Evaluates statutory approval versions, program formats, seat pools, and capacity rules.',
      deepDive:
        'Regulatory policy is not a collection of hardcoded boolean flags. Findings are evaluated against versioned statutory rules (e.g., AICTE Process Handbook 2024-27). If evidence is incomplete—such as an unuploaded migration certificate or pending transfer order—the system declares INSUFFICIENT_EVIDENCE rather than an accusatory fraud state.',
      syntheticExample: {
        title: 'Versioned Statutory Evaluation Context',
        fields: [
          { label: 'Statutory Rule ID', value: 'REG-AICTE-DUAL-PROG-V2.4', state: 'neutral' },
          { label: 'Rule Condition', value: 'Simultaneous Full-Time Degrees in Physical Mode', state: 'neutral' },
          { label: 'Evaluated Context', value: 'One Full-time B.Tech + One Evening Advanced Diploma', state: 'neutral' },
          { label: 'Policy Determination', value: 'PERMISSIBLE_EXCEPTION (Shift separation verified)', state: 'verified' },
          { label: 'Applicable Version', value: 'Gazette Notification 2022/AICTE-DEC-V2', state: 'verified' },
        ],
        invariantNote: 'Invariant: Policy evaluation is strictly decoupled from identity matching. A verified single person may legitimately hold multiple valid educational records.',
      },
      keyMechanism: 'Declarative rule ASTs evaluated against timestamped evidence graphs and sanctioned program metadata.',
    },
    {
      id: 4,
      layerName: 'Layer 4: Evidence Completeness',
      question: 'Can an authorized reviewer defend the conclusion?',
      badge: 'DECISION REPRODUCIBILITY',
      badgeType: 'verified',
      shortDesc: 'Traces artifact provenance, required prerequisites, and audit-ready chain of custody.',
      deepDive:
        'Every reconciliation conclusion must be defensible in an appellate or statutory audit. Layer 4 tracks the exact evidence bundle that supported a determination: digital signatures, scanned migration receipts, institution endorsements, and system logs. If a document is modified or revoked, dependent findings automatically trigger scheduled re-evaluation.',
      syntheticExample: {
        title: 'Cryptographic Audit & Evidence Dependency Package',
        fields: [
          { label: 'Evidence Bundle ID', value: 'EVD-2024-BUNDLE-44109', state: 'neutral' },
          { label: 'Primary Artifact', value: 'Institutional Transfer Approval Letter (Signed PDF)', state: 'verified' },
          { label: 'Issuing Authority', value: 'Registrar, Directorate of Technical Education', state: 'verified' },
          { label: 'Provenance Hash', value: 'sha256:7e8b91a0...44bc912', state: 'neutral' },
          { label: 'Completeness State', value: 'SUFFICIENT_FOR_ADJUDICATION', state: 'verified' },
        ],
        invariantNote: 'Invariant: Without reproducible evidence artifacts, a finding remains provisional and cannot be used to penalize an institution or student.',
      },
      keyMechanism: 'Immutable evidence manifests with SHA-256 provenance hashes and dependency graphs.',
    },
  ];

  const current = layers.find((l) => l.id === activeLayer) || layers[0];

  return (
    <section id="four-layer-model" className="section" style={{ backgroundColor: 'var(--bg-surface)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3rem' }}>
          <span className="eyebrow">
            <Layers size={14} color="var(--ink-muted)" />
            CONCEPTUAL FOUNDATION
          </span>
          <h2 className="section-title">
            Four questions. Four separate states of truth.
          </h2>
          <p className="section-subtitle">
            APAAR SETU avoids collapsing every student record into one simplistic verdict. Reporting, identity, policy, and evidence completeness are represented independently.
          </p>
        </div>

        {/* 4-Layer Interactive Selector & Stack */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(280px, 1fr) minmax(360px, 1.4fr)',
            gap: '2rem',
            alignItems: 'start',
          }}
          className="layer-grid"
        >
          {/* Left Column: Vertical Layer Selector */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {layers.map((layer) => {
              const isActive = layer.id === activeLayer;
              return (
                <button
                  key={layer.id}
                  type="button"
                  onClick={() => setActiveLayer(layer.id)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    textAlign: 'left',
                    padding: '1.25rem',
                    borderRadius: '8px',
                    border: `1.5px solid ${isActive ? 'var(--ink-primary)' : 'var(--border-subtle)'}`,
                    backgroundColor: isActive ? 'var(--bg-subtle)' : 'var(--bg-surface)',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                    boxShadow: isActive ? 'var(--shadow-sm)' : 'none',
                  }}
                  aria-pressed={isActive}
                >
                  <div style={{ display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        color: isActive ? 'var(--ink-primary)' : 'var(--ink-muted)',
                      }}
                    >
                      {layer.layerName}
                    </span>
                    <span
                      className={`badge badge-${layer.badgeType}`}
                      style={{ fontSize: '0.625rem' }}
                    >
                      {layer.badge}
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: '0.9375rem',
                      fontWeight: 600,
                      color: isActive ? 'var(--ink-primary)' : 'var(--ink-secondary)',
                      lineHeight: 1.35,
                      marginBottom: '0.35rem',
                    }}
                  >
                    {layer.question}
                  </div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--ink-muted)', lineHeight: 1.4 }}>
                    {layer.shortDesc}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right Column: Layer Detailed Deep Dive & Synthetic State */}
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-medium)',
              borderRadius: '10px',
              padding: '2rem',
              boxShadow: 'var(--shadow-md)',
            }}
          >
            {/* Header of Active Card */}
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem' }}>
              <div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-muted)' }}>
                  ACTIVE TRUTH LAYER 0{current.id}
                </span>
                <h3 style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.2rem' }}>
                  {current.question}
                </h3>
              </div>
              <span className={`badge badge-${current.badgeType}`}>
                {current.badge}
              </span>
            </div>

            {/* Deep Dive Paragraph */}
            <p style={{ fontSize: '0.9375rem', lineHeight: 1.65, color: 'var(--ink-secondary)', marginBottom: '1.75rem' }}>
              {current.deepDive}
            </p>

            {/* Synthetic Data Box */}
            <div
              style={{
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '1.25rem',
                marginBottom: '1.5rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--ink-secondary)' }}>
                  {current.syntheticExample.title}
                </span>
                <span className="badge badge-neutral" style={{ fontSize: '0.625rem' }}>
                  SYNTHETIC CASE STUDY
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '0.85rem' }}>
                {current.syntheticExample.fields.map((f, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      justifyContent: 'space-between',
                      fontSize: '0.8125rem',
                      padding: '0.35rem 0.5rem',
                      borderRadius: '4px',
                      backgroundColor: 'var(--bg-surface)',
                      border: '1px solid var(--border-faint)',
                    }}
                  >
                    <span style={{ color: 'var(--ink-muted)', fontWeight: 500 }}>{f.label}:</span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color:
                          f.state === 'verified'
                            ? 'var(--state-verified-text)'
                            : f.state === 'pending'
                            ? 'var(--state-pending-text)'
                            : 'var(--ink-primary)',
                      }}
                    >
                      {f.value}
                    </span>
                  </div>
                ))}
              </div>

              <div
                style={{
                  fontSize: '0.75rem',
                  fontStyle: 'italic',
                  color: 'var(--ink-secondary)',
                  borderTop: '1px dashed var(--border-medium)',
                  paddingTop: '0.65rem',
                  lineHeight: 1.5,
                }}
              >
                {current.syntheticExample.invariantNote}
              </div>
            </div>

            {/* Underlying System Mechanism */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem', fontSize: '0.8125rem', color: 'var(--ink-muted)' }}>
              <ArrowRight size={16} style={{ flexShrink: 0, marginTop: '0.15rem' }} color="var(--ink-primary)" />
              <div>
                <strong style={{ color: 'var(--ink-primary)' }}>System Implementation: </strong>
                {current.keyMechanism}
              </div>
            </div>
          </div>
        </div>

        {/* Visually Prominent Principle Callout */}
        <div
          style={{
            marginTop: '3.5rem',
            padding: '1.75rem 2rem',
            borderRadius: '10px',
            backgroundColor: '#0b132b',
            color: '#ffffff',
            border: '1px solid #1e293b',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                backgroundColor: 'rgba(45, 212, 191, 0.2)',
                color: '#2dd4bf',
              }}
            >
              ✓
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                letterSpacing: '0.08em',
                color: '#94a3b8',
                textTransform: 'uppercase',
              }}
            >
              Foundational Architectural Guarantee
            </span>
          </div>

          <div
            style={{
              fontSize: 'clamp(1.15rem, 2.4vw, 1.45rem)',
              fontWeight: 700,
              lineHeight: 1.35,
              color: '#ffffff',
              letterSpacing: '-0.015em',
            }}
          >
            An admission can remain counted while its identity is uncertain and its policy status remains unresolved.
          </div>

          <p style={{ fontSize: '0.875rem', color: '#94a3b8', lineHeight: 1.6, maxWidth: '52rem' }}>
            By maintaining strict separation across the Four Layers, institutions avoid false zero-counts, protect valid seat allotments during administrative inquiries, and produce auditable reconciliation records for regulatory oversight.
          </p>
        </div>
      </div>

      <style>{`
        @media (max-width: 860px) {
          .layer-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </section>
  );
};
