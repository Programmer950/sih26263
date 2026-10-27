import React from 'react';
import { Network, Scale, FileText, AlertCircle } from 'lucide-react';

export const ProblemSection: React.FC = () => {
  const challenges = [
    {
      code: 'CHALLENGE 01',
      title: 'Records across institutional boundaries',
      summary: 'Similar records are not necessarily the same person.',
      description:
        'Higher education institutions operate disparate registry formats, naming conventions, and local student ID schemas. Minor typographical differences, transliteration variations, or coincidental name matches across states must not be prematurely linked or conflated without provenance.',
      keyAspects: [
        'Local identifiers vary in structure, scope, and verification history',
        'Phonetic and orthographic similarities frequently produce false candidates',
        'An APAAR identifier must be evaluated as an identity assertion, not an unquestioned primary key',
      ],
      icon: Network,
    },
    {
      code: 'CHALLENGE 02',
      title: 'Reporting must remain accurate',
      summary: 'Uncertainty must not erase reported institutional admissions.',
      description:
        'Traditional deduplication tools often silently merge or drop suspected duplicates. In statutory education reporting, an institutional enrolment is a formal event with funding, seat quota, and regulatory ramifications. A finding cannot cause a reported admission to vanish.',
      keyAspects: [
        'Reported intake counts remain immutable and audited in an append-only ledger',
        'Suspected duplicates remain distinct reported entities until authorized adjudication',
        'Regulatory reporting preserves true institutional submissions regardless of downstream findings',
      ],
      icon: Scale,
    },
    {
      code: 'CHALLENGE 03',
      title: 'Policy requires context and evidence',
      summary: 'Policy determinations cannot rely on crude heuristics.',
      description:
        'Dual-degree permissions, institutional transfers, branch conversions, and sanctioned capacity limits cannot be evaluated with binary flags. What looks like an impermissible concurrent admission may be an authorized distance diploma, a completed migration, or an unfiled clearance certificate.',
      keyAspects: [
        'Rules must be evaluated against the exact versioned regulatory clauses in force',
        'Missing documentation must result in "Insufficient Evidence", never premature accusation',
        'Reconciliation findings require clear provenance dependencies before punitive action',
      ],
      icon: FileText,
    },
  ];

  return (
    <section className="section" style={{ backgroundColor: 'var(--bg-canvas)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3.5rem' }}>
          <span className="eyebrow">
            <AlertCircle size={14} color="var(--ink-muted)" />
            THE REGULATORY & TECHNICAL PROBLEM
          </span>
          <h2 className="section-title">
            Student-record reconciliation is more than duplicate detection.
          </h2>
          <p className="section-subtitle">
            Most administrative systems treat student records as flat database rows to be deduplicated. In high-stakes national higher education infrastructure, three structural realities make simple deduplication dangerous.
          </p>
        </div>

        {/* Editorial Layout: Structured 3-Column Editorial Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '2.5rem',
          }}
        >
          {challenges.map((challenge) => {
            const Icon = challenge.icon;
            return (
              <div
                key={challenge.code}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  borderTop: '2px solid var(--ink-primary)',
                  paddingTop: '1.5rem',
                }}
              >
                {/* Header with Code and Icon */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: 'var(--ink-muted)',
                      letterSpacing: '0.06em',
                    }}
                  >
                    {challenge.code}
                  </span>
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--bg-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Icon size={16} color="var(--ink-secondary)" />
                  </div>
                </div>

                {/* Title and Summary */}
                <h3
                  style={{
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    lineHeight: 1.3,
                    color: 'var(--ink-primary)',
                    marginBottom: '0.5rem',
                    letterSpacing: '-0.015em',
                  }}
                >
                  {challenge.title}
                </h3>
                <div
                  style={{
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    color: 'var(--state-pending-text)',
                    marginBottom: '1rem',
                  }}
                >
                  {challenge.summary}
                </div>

                {/* Description */}
                <p
                  style={{
                    fontSize: '0.875rem',
                    color: 'var(--ink-secondary)',
                    lineHeight: 1.65,
                    marginBottom: '1.5rem',
                    flexGrow: 1,
                  }}
                >
                  {challenge.description}
                </p>

                {/* Technical Takeaways List */}
                <div
                  style={{
                    borderTop: '1px solid var(--border-subtle)',
                    paddingTop: '1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.625rem',
                  }}
                >
                  {challenge.keyAspects.map((aspect, aspectIdx) => (
                    <div
                      key={aspectIdx}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '0.5rem',
                        fontSize: '0.78125rem',
                        color: 'var(--ink-muted)',
                        lineHeight: 1.5,
                      }}
                    >
                      <span
                        style={{
                          width: '4px',
                          height: '4px',
                          borderRadius: '50%',
                          backgroundColor: 'var(--ink-primary)',
                          marginTop: '0.45rem',
                          flexShrink: 0,
                        }}
                      />
                      <span>{aspect}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
