import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { EnterpriseLayout } from './components/layout/EnterpriseLayout';
import { PreservedShowcase } from './pages/PreservedShowcase';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Institutions } from './pages/Institutions';
import { StudentRepository } from './pages/StudentRepository';
import { DiscrepancyDashboard } from './pages/DiscrepancyDashboard';
import { AdmissionIntakeDashboard } from './pages/AdmissionIntakeDashboard';
import { CohortExplorer } from './pages/CohortExplorer';
import { DuplicateDetection } from './pages/DuplicateDetection';
import { VerificationPortal } from './pages/VerificationPortal';
import { RegulatoryDashboard } from './pages/RegulatoryDashboard';
import { DataSubmissions } from './pages/DataSubmissions';
import { ReconciliationCentre } from './pages/ReconciliationCentre';
import { CertificateViewer } from './pages/CertificateViewer';
import { ApaarValidation } from './pages/ApaarValidation';
import { ReviewResolution } from './pages/ReviewResolution';
import { RulesConfiguration } from './pages/RulesConfiguration';
import { AuditAccessHistory } from './pages/AuditAccessHistory';


// Route Guard for authenticated enterprise routes
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#F8FAFC',
          fontFamily: 'Inter, sans-serif',
          color: '#64748B',
          fontSize: '14px',
        }}
      >
        Initializing secure session...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Navigate to="/about-model" replace />} />
      <Route path="/about-model" element={<PreservedShowcase />} />
      <Route path="/login" element={<Login />} />

      {/* Protected Enterprise Platform Routes */}
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <EnterpriseLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/app/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="institutions" element={<Institutions />} />
        <Route path="students" element={<StudentRepository />} />

        {/* 13 Fully Functional Integrated Domain Modules */}
        <Route path="submissions" element={<DataSubmissions />} />
        <Route path="apaar-validation" element={<ApaarValidation />} />
        <Route
          path="admission-monitoring"
          element={<AdmissionIntakeDashboard />}
        />
        <Route
          path="duplicate-detection"
          element={<DuplicateDetection />}
        />
        <Route
          path="cohort-explorer"
          element={<CohortExplorer />}
        />
        <Route path="reconciliation" element={<ReconciliationCentre />} />
        <Route
          path="discrepancies"
          element={<DiscrepancyDashboard />}
        />
        <Route path="reviews" element={<ReviewResolution />} />
        <Route
          path="verification"
          element={<VerificationPortal />}
        />
        <Route path="certificates" element={<CertificateViewer />} />
        <Route
          path="reports"
          element={<RegulatoryDashboard />}
        />
        <Route
          path="regulatory-dashboard"
          element={<RegulatoryDashboard />}
        />
        <Route path="rules" element={<RulesConfiguration />} />
        <Route path="audit" element={<AuditAccessHistory />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/about-model" replace />} />
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
