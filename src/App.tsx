import React from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { ProblemSection } from './components/ProblemSection';
import { FourLayerModel } from './components/FourLayerModel';
import { ProofChainSection } from './components/ProofChainSection';
import { ReportingIntegrity } from './components/ReportingIntegrity';
import { IdentityReconciliation } from './components/IdentityReconciliation';
import { PolicyAwareReconciliation } from './components/PolicyAwareReconciliation';
import { ArchitectureSection } from './components/ArchitectureSection';
import { PrivacyResponsibleVerification } from './components/PrivacyResponsibleVerification';
import { ProjectStatusSection } from './components/ProjectStatusSection';
import { Footer } from './components/Footer';

export const App: React.FC = () => {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
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

export default App;
