import React, { useState } from 'react';
import { Eye, Shield, Globe } from 'lucide-react';

export const GovTopBar: React.FC = () => {
  const [fontSizeLevel, setFontSizeLevel] = useState<'sm' | 'md' | 'lg'>('md');
  const [isHighContrast, setIsHighContrast] = useState(false);
  const [lang, setLang] = useState<'EN' | 'HI'>('EN');

  // Handle font size scaling on document element
  const handleFontSize = (level: 'sm' | 'md' | 'lg') => {
    setFontSizeLevel(level);
    const root = document.documentElement;
    if (level === 'sm') {
      root.style.fontSize = '13px';
    } else if (level === 'md') {
      root.style.fontSize = '14px';
    } else if (level === 'lg') {
      root.style.fontSize = '16px';
    }
  };

  // Handle high contrast mode
  const toggleHighContrast = () => {
    const next = !isHighContrast;
    setIsHighContrast(next);
    if (next) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }
  };

  return (
    <div style={{ width: '100%', background: '#FFFFFF', borderBottom: '1px solid #D7DEE5' }}>
      {/* Topmost National Tricolour Accent Line */}
      <div className="gov-tricolour-ribbon" />

      {/* Top Utility Bar */}
      <div
        style={{
          background: '#0B1F36',
          color: '#E2E8F0',
          padding: '4px 24px',
          fontSize: '11.5px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontWeight: 700, color: '#FF9933' }}>भारत सरकार</span>
          <span style={{ color: '#64748B' }}>|</span>
          <span style={{ fontWeight: 600 }}>Government of India</span>
          <span style={{ color: '#64748B' }}>—</span>
          <span style={{ color: '#94A3B8' }}>Regulatory Demonstration Prototype (SIH26263)</span>
        </div>

        {/* Accessibility & Language Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Skip link */}
          <a
            href="#main-content"
            style={{ color: '#94A3B8', textDecoration: 'none', fontSize: '11px' }}
            className="hover:underline"
          >
            Skip to Main Content
          </a>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', borderLeft: '1px solid #1E293B', paddingLeft: '12px' }}>
            <span style={{ color: '#94A3B8', fontSize: '11px', marginRight: '4px' }}>Text Size:</span>
            <button
              onClick={() => handleFontSize('sm')}
              style={{
                background: fontSizeLevel === 'sm' ? '#174F82' : '#1E293B',
                color: '#FFFFFF',
                border: '1px solid #334155',
                borderRadius: '2px',
                padding: '1px 6px',
                fontSize: '10.5px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
              title="Small text"
            >
              A-
            </button>
            <button
              onClick={() => handleFontSize('md')}
              style={{
                background: fontSizeLevel === 'md' ? '#174F82' : '#1E293B',
                color: '#FFFFFF',
                border: '1px solid #334155',
                borderRadius: '2px',
                padding: '1px 6px',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
              title="Standard text"
            >
              A
            </button>
            <button
              onClick={() => handleFontSize('lg')}
              style={{
                background: fontSizeLevel === 'lg' ? '#174F82' : '#1E293B',
                color: '#FFFFFF',
                border: '1px solid #334155',
                borderRadius: '2px',
                padding: '1px 6px',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
              title="Large text"
            >
              A+
            </button>
          </div>

          {/* Contrast */}
          <button
            onClick={toggleHighContrast}
            style={{
              background: isHighContrast ? '#E58A24' : 'transparent',
              color: isHighContrast ? '#000000' : '#E2E8F0',
              border: '1px solid #334155',
              borderRadius: '2px',
              padding: '1px 8px',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Toggle High Contrast"
          >
            <Eye size={12} />
            <span>{isHighContrast ? 'Standard' : 'Contrast'}</span>
          </button>

          {/* Language Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', borderLeft: '1px solid #1E293B', paddingLeft: '12px' }}>
            <Globe size={12} color="#94A3B8" />
            <button
              onClick={() => setLang(lang === 'EN' ? 'HI' : 'EN')}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#38BDF8',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 600,
              }}
            >
              {lang === 'EN' ? 'हिन्दी' : 'English'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Identity Banner Header */}
      <div
        style={{
          padding: '14px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          background: '#FFFFFF',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {/* State Emblem of India Logo */}
          <img
            src="/emblem.png"
            alt="State Emblem of India"
            style={{
              height: '54px',
              width: 'auto',
              objectFit: 'contain',
              flexShrink: 0,
            }}
          />

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1
                style={{
                  fontSize: '20px',
                  fontWeight: 900,
                  color: '#12345A',
                  margin: 0,
                  letterSpacing: '-0.3px',
                }}
              >
                APAAR SETU
              </h1>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  background: '#FFF4E5',
                  color: '#C05621',
                  border: '1px solid #FBD38D',
                  padding: '1px 6px',
                  borderRadius: '2px',
                  letterSpacing: '0.4px',
                }}
              >
                SIH DEMO PROTOTYPE
              </span>
            </div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#174F82', margin: '1px 0' }}>
              Longitudinal Student Data Integrity & Regulatory Verification Platform
            </div>
            <div style={{ fontSize: '11px', color: '#5F6B76' }}>
              Ministry of Education / AICTE Problem Statement Demonstration Portal | SIH26263
            </div>
          </div>
        </div>

        {/* Right side Institutional Badges */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            fontSize: '11.5px',
            color: '#4A5568',
            textAlign: 'right',
          }}
        >
          <div style={{ borderRight: '1px solid #D7DEE5', paddingRight: '12px' }}>
            <div style={{ fontWeight: 700, color: '#12345A' }}>Academic Cycles</div>
            <div style={{ color: '#718096', fontSize: '11px' }}>2024-25 &bull; 2025-26</div>
          </div>
          <div>
            <div style={{ fontWeight: 700, color: '#23834A', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Shield size={13} />
              <span>DPDPA & ISO 27001 Redaction</span>
            </div>
            <div style={{ color: '#718096', fontSize: '11px' }}>SHA-256 Chained Ledger</div>
          </div>
        </div>
      </div>
    </div>
  );
};
