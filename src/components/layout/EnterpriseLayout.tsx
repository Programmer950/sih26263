import React, { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { GovTopBar } from './GovTopBar';
import { GovFooter } from './GovFooter';
import {
  LucideIcon,
  LayoutDashboard,
  Building2,
  GraduationCap,
  UploadCloud,
  ShieldCheck,
  CheckCircle2,
  GitCompare,
  Layers,
  Scale,
  AlertTriangle,
  FileCheck,
  Search,
  QrCode,
  BarChart3,
  Settings,
  History,
  LogOut,
  ChevronRight,
  Menu,
  X,
  ExternalLink,
  Building,
} from 'lucide-react';

interface NavSection {
  title: string;
  items: {
    name: string;
    path: string;
    icon: LucideIcon;
    badge?: string;
  }[];
}

const navSections: NavSection[] = [
  {
    title: '1. OVERVIEW & MONITORING',
    items: [
      { name: 'Overview Dashboard', path: '/app/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: '2. INSTITUTIONAL REGISTRIES',
    items: [
      { name: 'Institution Management', path: '/app/institutions', icon: Building2 },
      { name: 'Student Repository', path: '/app/students', icon: GraduationCap },
      { name: 'Data Submissions', path: '/app/submissions', icon: UploadCloud },
      { name: 'APAAR Validation Registry', path: '/app/apaar-validation', icon: ShieldCheck },
    ],
  },
  {
    title: '3. REGULATORY MONITORING',
    items: [
      { name: 'Admission & Intake', path: '/app/admission-monitoring', icon: CheckCircle2 },
      { name: 'Cross-Institution Checks', path: '/app/duplicate-detection', icon: GitCompare },
      { name: 'Cohort Explorer (120 vs 120)', path: '/app/cohort-explorer', icon: Layers, badge: 'Key' },
      { name: 'Reconciliation Centre', path: '/app/reconciliation', icon: Scale },
      { name: 'Discrepancy Centre', path: '/app/discrepancies', icon: AlertTriangle },
      { name: 'Review & Resolution', path: '/app/reviews', icon: FileCheck },
    ],
  },
  {
    title: '4. VERIFICATION SERVICES',
    items: [
      { name: 'Verification Portal', path: '/app/verification', icon: Search, badge: 'Live' },
      { name: 'Certificate Identity', path: '/app/certificates', icon: QrCode },
    ],
  },
  {
    title: '5. POLICY & AUDIT',
    items: [
      { name: 'Reports & Analytics', path: '/app/reports', icon: BarChart3 },
      { name: 'Rules & Configuration', path: '/app/rules', icon: Settings },
      { name: 'Audit & Access Ledger', path: '/app/audit', icon: History },
    ],
  },
];

export const EnterpriseLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getRoleBadgeStyle = (role?: string) => {
    switch (role) {
      case 'SYSTEM_ADMIN':
        return { background: '#12345A', color: '#FFFFFF', border: '1px solid #1E4F8A' };
      case 'REGULATORY_REVIEWER':
        return { background: '#0D7A68', color: '#FFFFFF', border: '1px solid #149680' };
      case 'INSTITUTION_ADMIN':
        return { background: '#1E40AF', color: '#FFFFFF', border: '1px solid #3B82F6' };
      case 'STUDENT_VERIFIER':
        return { background: '#B7791F', color: '#FFFFFF', border: '1px solid #D69E2E' };
      default:
        return { background: '#4A5568', color: '#FFFFFF', border: '1px solid #718096' };
    }
  };

  // Derive breadcrumb from active route
  const getBreadcrumbTitle = () => {
    const p = location.pathname;
    for (const sec of navSections) {
      const match = sec.items.find((i) => i.path === p);
      if (match) return { section: sec.title.replace(/^\d+\.\s*/, ''), item: match.name };
    }
    return { section: 'National Platform', item: 'Administrative Workspace' };
  };

  const breadcrumb = getBreadcrumbTitle();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: '#F4F6F8' }}>
      {/* Top Formal Government Header */}
      <GovTopBar />

      <div style={{ display: 'flex', flexGrow: 1, minHeight: 0 }}>
        {/* Government Administrative Sidebar */}
        <aside
          style={{
            width: sidebarOpen ? '270px' : '0px',
            background: '#12345A',
            color: '#E2E8F0',
            transition: 'width 0.2s ease',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid #0B1F36',
            flexShrink: 0,
            zIndex: 30,
          }}
        >
          {/* Active Jurisdiction Scope Card */}
          <div
            style={{
              padding: '12px 16px',
              background: '#0B1F36',
              borderBottom: '1px solid #1E3A5F',
              display: 'flex',
              gap: '12px',
              alignItems: 'center',
            }}
          >
            <img
              src="/emblem.png"
              alt="State Emblem of India"
              style={{
                height: '36px',
                width: 'auto',
                objectFit: 'contain',
                filter: 'brightness(0) invert(1)',
                opacity: 0.85,
                flexShrink: 0,
              }}
            />
            <div style={{ minWidth: 0, flexGrow: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', textTransform: 'uppercase', color: '#E58A24', fontWeight: 800, letterSpacing: '0.6px' }}>
                <Building size={12} />
                <span>Regulatory Jurisdiction</span>
              </div>
              <div
                style={{
                  fontSize: '13px',
                  fontWeight: 700,
                  color: '#FFFFFF',
                  marginTop: '2px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
                title={user?.institution_name || 'AICTE Central Authority'}
              >
                {user?.institution_name || 'AICTE Central Authority'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '2px', fontSize: '11px', color: '#94A3B8' }}>
                <span>Code: <strong style={{ color: '#E2E8F0' }}>{user?.institution_code || 'CENTRAL-01'}</strong></span>
                <span style={{ background: '#174F82', color: '#FFFFFF', padding: '1px 5px', borderRadius: '2px', fontSize: '10px' }}>ACTIVE</span>
              </div>
            </div>
          </div>

          {/* Categorized Navigation */}
          <nav
            style={{
              flexGrow: 1,
              overflowY: 'auto',
              padding: '12px 8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            {navSections.map((section, sIdx) => (
              <div key={sIdx}>
                <div
                  style={{
                    fontSize: '10.5px',
                    fontWeight: 800,
                    color: '#94A3B8',
                    padding: '4px 10px 6px',
                    letterSpacing: '0.5px',
                    textTransform: 'uppercase',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                    marginBottom: '4px',
                  }}
                >
                  {section.title}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  {section.items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        style={({ isActive }) => ({
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '7px 10px',
                          borderRadius: '3px',
                          textDecoration: 'none',
                          fontSize: '12.5px',
                          fontWeight: isActive ? 700 : 500,
                          color: isActive ? '#FFFFFF' : '#CBD5E1',
                          background: isActive ? '#174F82' : 'transparent',
                          borderLeft: isActive ? '3px solid #E58A24' : '3px solid transparent',
                          transition: 'all 0.12s ease',
                        })}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                          <Icon size={15} style={{ flexShrink: 0, color: '#94A3B8' }} />
                          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {item.name}
                          </span>
                        </div>
                        {item.badge && (
                          <span
                            style={{
                              fontSize: '9.5px',
                              fontWeight: 800,
                              background: '#E58A24',
                              color: '#FFFFFF',
                              padding: '1px 5px',
                              borderRadius: '2px',
                              letterSpacing: '0.3px',
                            }}
                          >
                            {item.badge}
                          </span>
                        )}
                      </NavLink>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>

          {/* Sidebar Footer Link */}
          <div style={{ padding: '10px 12px', borderTop: '1px solid #0B1F36', background: '#0B1F36' }}>
            <NavLink
              to="/about-model"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                borderRadius: '3px',
                background: '#12345A',
                color: '#38BDF8',
                fontSize: '11.5px',
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              <span>SIH Problem Statement Model</span>
              <ExternalLink size={12} />
            </NavLink>
          </div>
        </aside>

        {/* Main Content Area */}
        <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
          {/* Top Administrative Breadcrumb & User Context Bar */}
          <div
            style={{
              background: '#FFFFFF',
              borderBottom: '1px solid #D7DEE5',
              padding: '8px 24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
              flexShrink: 0,
            }}
          >
            {/* Toggle & Breadcrumbs */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                style={{
                  background: '#F1F5F9',
                  border: '1px solid #CBD5E1',
                  cursor: 'pointer',
                  color: '#12345A',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '5px 8px',
                  borderRadius: '3px',
                }}
                title="Toggle Navigation"
              >
                {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', color: '#5F6B76' }}>
                <span style={{ color: '#174F82', fontWeight: 600 }}>Portal</span>
                <ChevronRight size={13} />
                <span>{breadcrumb.section}</span>
                <ChevronRight size={13} />
                <span style={{ color: '#12345A', fontWeight: 700 }}>{breadcrumb.item}</span>
              </div>
            </div>

            {/* Authenticated Identity & Session Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              {/* Role Indicator Badge */}
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 800,
                  padding: '3px 9px',
                  borderRadius: '3px',
                  letterSpacing: '0.4px',
                  ...getRoleBadgeStyle(user?.role),
                }}
              >
                {user?.role?.replace('_', ' ')}
              </span>

              {/* User Identity */}
              <div style={{ textAlign: 'right', lineHeight: 1.2 }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#12345A' }}>{user?.name}</div>
                <div style={{ fontSize: '11px', color: '#5F6B76' }}>{user?.email}</div>
              </div>

              {/* Logout Button */}
              <button
                onClick={handleLogout}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '5px 10px',
                  borderRadius: '3px',
                  border: '1px solid #CBD5E1',
                  background: '#F8FAFC',
                  color: '#B42318',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: 700,
                }}
                title="End session and revoke JWT credentials"
              >
                <LogOut size={13} />
                <span>Logout</span>
              </button>
            </div>
          </div>

          {/* Main Module Content Body */}
          <main
            id="main-content"
            style={{
              flexGrow: 1,
              overflowY: 'auto',
              padding: '20px 28px',
              background: '#F4F6F8',
            }}
          >
            <Outlet />
          </main>

          {/* Persistent Government Portal Footer */}
          <GovFooter />
        </div>
      </div>
    </div>
  );
};
