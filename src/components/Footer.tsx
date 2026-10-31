import React from 'react';
import { ArrowUpRight } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer
      style={{
        backgroundColor: '#0b132b',
        color: '#ffffff',
        borderTop: '1px solid #1e293b',
        paddingTop: '3.5rem',
        paddingBottom: '3.5rem',
      }}
    >
      <div className="container">
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: '2.5rem',
            paddingBottom: '2.5rem',
            borderBottom: '1px solid #1e293b',
          }}
        >
          {/* Brand & Tagline */}
          <div style={{ maxWidth: '28rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.85rem' }}>
              <img
                src="/emblem.png"
                alt="State Emblem of India"
                style={{
                  height: '32px',
                  width: 'auto',
                  objectFit: 'contain',
                  filter: 'brightness(0) invert(1)',
                  opacity: 0.9,
                }}
              />
              <span style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#ffffff' }}>
                APAAR SETU
              </span>
            </div>

            <p style={{ fontSize: '0.9375rem', fontWeight: 500, color: '#94a3b8', lineHeight: 1.5, marginBottom: '0.75rem' }}>
              Every admission accounted for. Every decision traceable.
            </p>

            <p style={{ fontSize: '0.75rem', color: '#64748b', lineHeight: 1.5 }}>
              Post-admission student-record reconciliation and verification platform architecture designed for institutional integrity.
            </p>
          </div>

          {/* Project Coordinates */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8125rem' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', fontWeight: 600, color: '#38bdf8', letterSpacing: '0.06em' }}>
              PROJECT SPECIFICATION
            </div>
            <div style={{ color: '#cbd5e1' }}>Smart India Hackathon 2026</div>
            <div style={{ color: '#cbd5e1' }}>Problem Statement SIH26263</div>
            <div style={{ color: '#cbd5e1' }}>Team Code Zero · ID 197410</div>
          </div>

          {/* Navigation Links */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8125rem' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6875rem', fontWeight: 600, color: '#38bdf8', letterSpacing: '0.06em' }}>
              NAVIGATION
            </div>
            <a
              href="#overview"
              style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.15s ease' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
            >
              Overview
            </a>
            <a
              href="#four-layer-model"
              style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.15s ease' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
            >
              Four-Layer Truth Model
            </a>
            <a
              href="#proof-chain"
              style={{
                color: '#2dd4bf',
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontWeight: 600,
              }}
            >
              <span>Reconciliation Proof Chain</span>
              <ArrowUpRight size={14} />
            </a>
            <a
              href="#project-status"
              style={{ color: '#94a3b8', textDecoration: 'none', transition: 'color 0.15s ease' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
            >
              Project Status
            </a>
            <a
              href="/login"
              style={{
                color: '#E58A24',
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontWeight: 700,
                marginTop: '0.25rem',
              }}
            >
              <span>Launch Regulatory Portal</span>
              <ArrowUpRight size={14} />
            </a>
          </div>
        </div>

        {/* Bottom Notice */}
        <div
          style={{
            paddingTop: '2rem',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
            fontSize: '0.75rem',
            color: '#64748b',
          }}
        >
          <div>
            © 2026 APAAR SETU · Smart India Hackathon Prototype Project.
          </div>
          <div>
            Built with rigorous invariants for national educational integrity.
          </div>
        </div>
      </div>
    </footer>
  );
};
