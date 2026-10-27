import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: 'Overview', href: '#overview' },
    { label: 'Four-Layer Model', href: '#four-layer-model' },
    { label: 'Proof Chain', href: '#proof-chain' },
    { label: 'Reporting Integrity', href: '#reporting-integrity' },
    { label: 'Identity Matching', href: '#identity-matching' },
    { label: 'Architecture', href: '#architecture' },
    { label: 'Project Status', href: '#project-status' },
  ];

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        backgroundColor: isScrolled ? 'rgba(248, 248, 246, 0.92)' : 'var(--bg-canvas)',
        backdropFilter: isScrolled ? 'blur(10px)' : 'none',
        borderBottom: `1px solid ${isScrolled ? 'var(--border-subtle)' : 'transparent'}`,
        transition: 'background-color 0.2s ease, border-color 0.2s ease',
      }}
    >
      <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '4.25rem' }}>
        {/* Brand wordmark + geometric symbol */}
        <a
          href="#"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            textDecoration: 'none',
            color: 'inherit',
          }}
          aria-label="APAAR SETU Home"
        >
          {/* Custom geometric symbol: connected records bridge */}
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              backgroundColor: '#0b132b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <circle cx="5" cy="7" r="2.5" fill="#38bdf8" />
              <circle cx="19" cy="17" r="2.5" fill="#0d9488" />
              <path d="M5 7h6a4 4 0 0 1 4 4v2a4 4 0 0 1 4 4" stroke="#0d9488" strokeWidth="2" strokeLinecap="round" />
              <path d="M19 7h-4a4 4 0 0 0-4 4v2" stroke="#38bdf8" strokeWidth="1.75" strokeDasharray="2 2" strokeLinecap="round" />
              <circle cx="12" cy="12" r="1.75" fill="#d97706" />
            </svg>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontWeight: 700, fontSize: '1.05rem', letterSpacing: '-0.02em', color: 'var(--ink-primary)' }}>
                APAAR SETU
              </span>
            </div>
            <div style={{ fontSize: '0.625rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', letterSpacing: '0.04em' }}>
              RECONCILIATION PLATFORM
            </div>
          </div>
        </a>

        {/* Desktop Navigation */}
        <nav
          style={{ display: 'none', alignItems: 'center', gap: '1.5rem' }}
          className="desktop-nav"
          aria-label="Main Navigation"
        >
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              style={{
                fontSize: '0.8125rem',
                fontWeight: 500,
                color: 'var(--ink-secondary)',
                textDecoration: 'none',
                transition: 'color var(--transition-fast)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--ink-primary)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--ink-secondary)')}
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div
            className="badge badge-pending"
            style={{
              padding: '0.3rem 0.65rem',
              fontSize: '0.6875rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: 'var(--state-pending)',
                display: 'inline-block',
                boxShadow: '0 0 0 2px rgba(217, 119, 6, 0.2)',
              }}
            />
            <span>PROTOTYPE IN DEVELOPMENT</span>
          </div>

          {/* Mobile hamburger button */}
          <button
            type="button"
            className="mobile-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'none',
              border: '1px solid var(--border-medium)',
              borderRadius: '6px',
              padding: '0.4rem',
              color: 'var(--ink-primary)',
              cursor: 'pointer',
            }}
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div
          style={{
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-surface)',
            padding: '1.25rem 1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}
        >
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              style={{
                fontSize: '0.875rem',
                fontWeight: 500,
                color: 'var(--ink-primary)',
                textDecoration: 'none',
                padding: '0.35rem 0',
              }}
            >
              {link.label}
            </a>
          ))}
          <div style={{ paddingTop: '0.75rem', borderTop: '1px solid var(--border-faint)', fontSize: '0.75rem', color: 'var(--ink-muted)' }}>
            SIH 2026 · Problem Statement 26263 · Team Code Zero
          </div>
        </div>
      )}

      {/* Responsive media query styling */}
      <style>{`
        @media (min-width: 992px) {
          .desktop-nav {
            display: flex !important;
          }
          .mobile-toggle {
            display: none !important;
          }
        }
      `}</style>
    </header>
  );
};
