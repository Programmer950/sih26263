import React from 'react';
import { Database, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

interface PlaceholderProps {
  moduleNumber: number;
  title: string;
  milestone: string;
  description: string;
  keyEntities: string[];
  signature?: boolean;
}

export const PlaceholderModule: React.FC<PlaceholderProps> = ({
  moduleNumber,
  title,
  milestone,
  description,
  keyEntities,
  signature,
}) => {
  return (
    <div style={{ maxWidth: '880px' }}>
      {/* Title */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <span
            style={{
              background: signature ? '#0D9488' : '#1E293B',
              color: '#FFFFFF',
              fontSize: '11px',
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: '4px',
            }}
          >
            {signature ? 'Signature Innovation' : `Module ${moduleNumber}`}
          </span>
          <span
            style={{
              background: '#EFF6FF',
              color: '#2563EB',
              fontSize: '11.5px',
              fontWeight: 600,
              padding: '3px 8px',
              borderRadius: '4px',
            }}
          >
            {milestone}
          </span>
        </div>
        <h1 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', margin: '0 0 8px 0', letterSpacing: '-0.3px' }}>
          {title}
        </h1>
        <p style={{ fontSize: '14px', color: '#64748B', margin: 0, lineHeight: 1.5 }}>
          {description}
        </p>
      </div>

      {/* Architecture Spec Card */}
      <div style={{ background: '#FFFFFF', borderRadius: '10px', border: '1px solid #E2E8F0', padding: '24px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <Database size={16} color="#0D9488" />
          <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#0F172A', margin: 0 }}>
            Governing Relational Schema Entities (PostgreSQL)
          </h3>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '18px' }}>
          {keyEntities.map((entity) => (
            <span
              key={entity}
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '12px',
                background: '#F1F5F9',
                color: '#334155',
                padding: '4px 10px',
                borderRadius: '6px',
                border: '1px solid #E2E8F0',
                fontWeight: 600,
              }}
            >
              {entity}
            </span>
          ))}
        </div>

        <div style={{ fontSize: '13px', color: '#475569', lineHeight: 1.6, background: '#F8FAFC', padding: '14px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
          <strong>Implementation State:</strong> Database schemas and OpenAPI contracts have been finalized in Milestone 0 architecture v1.1. Backend foundational models and PostgreSQL persistence are live. Full vertical slice implementation is scheduled for <strong>{milestone}</strong>.
        </div>
      </div>

      {/* Navigation Helper */}
      <div style={{ display: 'flex', gap: '12px' }}>
        <Link
          to="/app/dashboard"
          style={{
            background: '#0B192C',
            color: '#FFFFFF',
            padding: '9px 16px',
            borderRadius: '6px',
            textDecoration: 'none',
            fontSize: '13px',
            fontWeight: 600,
          }}
        >
          Return to Dashboard
        </Link>
        <Link
          to="/about-model"
          style={{
            background: '#FFFFFF',
            border: '1px solid #CBD5E1',
            color: '#0F172A',
            padding: '9px 16px',
            borderRadius: '6px',
            textDecoration: 'none',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>Review Four-Layer Theoretical Model</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
};
