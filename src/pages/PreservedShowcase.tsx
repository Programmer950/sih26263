import React from 'react';
import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Hero } from '../components/Hero';
import { ProblemSection } from '../components/ProblemSection';
import { FourLayerModel } from '../components/FourLayerModel';
import { ProofChainSection } from '../components/ProofChainSection';
import { ReportingIntegrity } from '../components/ReportingIntegrity';
import { IdentityReconciliation } from '../components/IdentityReconciliation';
import { PolicyAwareReconciliation } from '../components/PolicyAwareReconciliation';
import { ArchitectureSection } from '../components/ArchitectureSection';
import { PrivacyResponsibleVerification } from '../components/PrivacyResponsibleVerification';
import { ProjectStatusSection } from '../components/ProjectStatusSection';
import { Footer } from '../components/Footer';
import { ArrowRight, ShieldCheck } from 'lucide-react';

export const PreservedShowcase: React.FC = () => {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#F8FAFC' }}>
      {/* Official Government Tricolour Ribbon */}
      <div className="gov-tricolour-ribbon" />

      {/* Top Formal E-Governance Masthead Bar */}
      <div
        style={{
          background: '#0B1F36',
          color: '#FFFFFF',
          padding: '8px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '12px',
          borderBottom: '1px solid #1E3A5F',
          zIndex: 50,
          position: 'sticky',
          top: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldCheck size={16} color="#E58A24" />
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ color: '#E2E8F0', fontWeight: 600 }}>
              भारत सरकार | Government of India — Smart India Hackathon (SIH26263)
            </span>
            <span
              style={{
                background: '#174F82',
                color: '#FFFFFF',
                fontSize: '10px',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '2px',
                letterSpacing: '0.4px',
              }}
            >
              ARCHITECTURAL RECONCILIATION SPECIFICATION
            </span>
          </div>
        </div>

        <Link
          to="/login"
          style={{
            background: '#E58A24',
            color: '#FFFFFF',
            padding: '5px 14px',
            borderRadius: '3px',
            textDecoration: 'none',
            fontSize: '11.5px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            letterSpacing: '0.3px',
          }}
        >
          <span>ACCESS LIVE REGULATORY PORTAL</span>
          <ArrowRight size={13} />
        </Link>
      </div>

      <Navbar />
      <main style={{ flexGrow: 1 }}>
        <Hero />
        <ProblemSection />
        <FourLayerModel />
        <ProofChainSection />
        <ReportingIntegrity />
        <IdentityReconciliation />
        <PolicyAwareReconciliation />
        <ArchitectureSection />
        <PrivacyResponsibleVerification />
        <ProjectStatusSection />
      </main>
      <Footer />
    </div>
  );
};

