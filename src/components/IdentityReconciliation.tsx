import React, { useState } from 'react';
import { UserCheck, ShieldAlert, Check, Link2, Unlink } from 'lucide-react';

export const IdentityReconciliation: React.FC = () => {
  // Local state for reviewer decision simulation
  const [reviewDecision, setReviewDecision] = useState<'pending' | 'linked' | 'separated'>('pending');

  const matchingSteps = [
    {
      step: '01',
      title: 'Exact Identifier Matching',
      desc: 'Deterministic indexing on institution-scoped roll numbers, state board credentials, and verified assertions.',
    },
    {
      step: '02',
      title: 'Candidate Multi-Pass Generation',
      desc: 'Phonetic blocking (Metaphone) and tokenized trigram passes generate candidate pairs without combinatorial explosion.',
    },
    {
      step: '03',
      title: 'Field-Level Vector Comparison',
      desc: 'Independent evaluation of full names, birthdates, secondary credentials, parent names, and district codes.',
    },
    {
      step: '04',
      title: 'Controlled Probabilistic Matching',
      desc: 'Optional Fellegi-Sunter scoring deployed strictly if it improves held-out benchmark accuracy over deterministic baseline.',
    },
    {
      step: '05',
      title: 'Authorized Human Determination',
      desc: 'Reviewers record reasoned, reversible decisions backed by verifiable evidence. Zero algorithmic auto-merges.',
    },
  ];

  return (
    <section id="identity-matching" className="section" style={{ backgroundColor: 'var(--bg-surface)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ maxWidth: '52rem', marginBottom: '3rem' }}>
          <span className="eyebrow">
            <UserCheck size={14} color="var(--ink-muted)" />
            IDENTITY RECONCILIATION DISCIPLINE
          </span>
          <h2 className="section-title">
            A possible match is a question, not a verdict.
          </h2>
          <p className="section-subtitle">
            Algorithmic candidate generation helps reviewers discover potential connections, but similar names or proximate birthdates never trigger automated record merges.
          </p>
        </div>

        {/* 5-Step Proposed Sequence */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '1.25rem',
            marginBottom: '3rem',
          }}
        >
          {matchingSteps.map((s) => (
            <div
              key={s.step}
              style={{
                backgroundColor: 'var(--bg-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.8125rem',
                  fontWeight: 700,
                  color: 'var(--ink-muted)',
                  marginBottom: '0.5rem',
                }}
              >
                PASS {s.step}
              </div>
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)', marginBottom: '0.5rem' }}>
                {s.title}
              </h3>
              <p style={{ fontSize: '0.78125rem', color: 'var(--ink-secondary)', lineHeight: 1.5, flexGrow: 1 }}>
                {s.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Interactive Comparison Panel with Synthetic Records */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-medium)',
            borderRadius: '12px',
            boxShadow: 'var(--shadow-sm)',
            overflow: 'hidden',
            marginBottom: '2.5rem',
          }}
        >
          {/* Header */}
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
              <span className="eyebrow" style={{ color: 'var(--ink-primary)' }}>
                ILLUSTRATIVE FIELD-LEVEL CANDIDATE COMPARISON
              </span>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--ink-primary)', marginTop: '0.2rem' }}>
                Candidate Pair #CP-2024-912 · Evaluation Matrix
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="badge badge-neutral">SYNTHETIC CANDIDATE DATA</span>
              {reviewDecision === 'pending' && (
                <span className="badge badge-pending">PENDING AUTHORIZED REVIEW</span>
              )}
              {reviewDecision === 'linked' && (
                <span className="badge badge-verified">HUMAN-CONFIRMED SAME PERSON</span>
              )}
              {reviewDecision === 'separated' && (
                <span className="badge badge-blueprint">CONFIRMED SEPARATE INDIVIDUALS</span>
              )}
            </div>
          </div>

          {/* Comparison Table */}
          <div style={{ overflowX: 'auto', padding: '1.5rem' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                textAlign: 'left',
                fontSize: '0.8125rem',
              }}
            >
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-subtle)', color: 'var(--ink-muted)' }}>
                  <th style={{ padding: '0.75rem 0.5rem', fontWeight: 600, width: '22%' }}>ATTRIBUTION FIELD</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontWeight: 600, width: '30%' }}>RECORD A (NIT WEST)</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontWeight: 600, width: '30%' }}>RECORD B (STATE ENGG)</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontWeight: 600, width: '18%' }}>FIELD STATUS</th>
                </tr>
              </thead>
              <tbody style={{ fontFamily: 'var(--font-mono)' }}>
                <tr style={{ borderBottom: '1px solid var(--border-faint)' }}>
                  <td style={{ padding: '0.85rem 0.5rem', fontFamily: 'var(--font-sans)', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    Student Legal Name
                  </td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-primary)' }}>Rohit V. Patil</td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-primary)' }}>Rohit Patil</td>
                  <td style={{ padding: '0.85rem 0.5rem' }}>
                    <span className="badge badge-pending" style={{ fontSize: '0.625rem' }}>
                      Fuzzy 94% Match
                    </span>
                  </td>
                </tr>

                <tr style={{ borderBottom: '1px solid var(--border-faint)' }}>
                  <td style={{ padding: '0.85rem 0.5rem', fontFamily: 'var(--font-sans)', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    Date of Birth
                  </td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-primary)' }}>2005-08-12</td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-primary)' }}>2005-08-12</td>
                  <td style={{ padding: '0.85rem 0.5rem' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.625rem' }}>
                      Exact Match
                    </span>
                  </td>
                </tr>

                <tr style={{ borderBottom: '1px solid var(--border-faint)' }}>
                  <td style={{ padding: '0.85rem 0.5rem', fontFamily: 'var(--font-sans)', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    Father / Guardian Name
                  </td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-primary)' }}>Vijay Patil</td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-primary)' }}>Vijay Patil</td>
                  <td style={{ padding: '0.85rem 0.5rem' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.625rem' }}>
                      Exact Match
                    </span>
                  </td>
                </tr>

                <tr style={{ borderBottom: '1px solid var(--border-faint)' }}>
                  <td style={{ padding: '0.85rem 0.5rem', fontFamily: 'var(--font-sans)', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    Class X Roll / Board ID
                  </td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-primary)' }}>MH-2021-99214</td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-primary)' }}>MH-2021-99214</td>
                  <td style={{ padding: '0.85rem 0.5rem' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.625rem' }}>
                      Exact Match
                    </span>
                  </td>
                </tr>

                <tr style={{ borderBottom: '1px solid var(--border-faint)' }}>
                  <td style={{ padding: '0.85rem 0.5rem', fontFamily: 'var(--font-sans)', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    Enrolled Programme
                  </td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-secondary)' }}>B.Tech Computer Engg</td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-secondary)' }}>B.Tech Info Tech</td>
                  <td style={{ padding: '0.85rem 0.5rem' }}>
                    <span className="badge badge-neutral" style={{ fontSize: '0.625rem' }}>
                      Distinct Degrees
                    </span>
                  </td>
                </tr>

                <tr>
                  <td style={{ padding: '0.85rem 0.5rem', fontFamily: 'var(--font-sans)', fontWeight: 600, color: 'var(--ink-primary)' }}>
                    Institutional Transfer / NOC
                  </td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-muted)' }}>Not Filed</td>
                  <td style={{ padding: '0.85rem 0.5rem', color: 'var(--ink-muted)' }}>Not Filed</td>
                  <td style={{ padding: '0.85rem 0.5rem' }}>
                    <span className="badge badge-pending" style={{ fontSize: '0.625rem' }}>
                      Missing Evidence
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Reviewer Simulation Actions */}
          <div
            style={{
              padding: '1.25rem 1.5rem',
              backgroundColor: '#fafaf8',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
            }}
          >
            <div>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--ink-primary)' }}>
                Illustrative Reviewer Actions (Local UI Simulation Only)
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)' }}>
                Updates local prototype view. Does not save to any live database.
              </div>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
              <button
                type="button"
                className={`btn btn-sm ${reviewDecision === 'linked' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setReviewDecision('linked')}
              >
                <Link2 size={14} />
                <span>Link After Review (Hypothetical)</span>
              </button>
              <button
                type="button"
                className={`btn btn-sm ${reviewDecision === 'separated' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setReviewDecision('separated')}
              >
                <Unlink size={14} />
                <span>Keep Separate</span>
              </button>
              {reviewDecision !== 'pending' && (
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={() => setReviewDecision('pending')}
                >
                  <span>Reset Decision</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Two Concrete Safeguards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
          <div
            style={{
              padding: '1.5rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-surface)',
              border: '1.5px solid var(--state-pending-border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
              <ShieldAlert size={18} color="var(--state-pending-text)" />
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                Safeguard 1: Similar names alone do not establish identity
              </h3>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              Across a nation with millions of enrolled students, high demographic overlap is expected. Phonetic, token, or string similarity produces investigation candidates only; legal linkage requires verified provenance.
            </p>
          </div>

          <div
            style={{
              padding: '1.5rem',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-surface)',
              border: '1.5px solid var(--state-verified-border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
              <Check size={18} color="var(--state-verified-text)" />
              <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: 'var(--ink-primary)' }}>
                Safeguard 2: Identity matching never automatically changes reported counts
              </h3>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--ink-secondary)', lineHeight: 1.6 }}>
              Even when an authorized reviewer confirms that two admissions represent the same person, neither institution's reported admission count is altered without a statutory deregistration or institutional withdrawal event.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
