import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { GovTopBar } from '../components/layout/GovTopBar';
import { GovFooter } from '../components/layout/GovFooter';
import {
  Lock,
  Mail,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  Eye,
  EyeOff,
  Key,
} from 'lucide-react';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const queryParams = new URLSearchParams(location.search);
  const wasRevoked = queryParams.get('revoked') === 'true';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      navigate('/app/dashboard');
    } catch (err: any) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Authentication failed. Please verify your credentials or server status.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#F4F6F8' }}>
      {/* Top Government Ribbon & Identity */}
      <GovTopBar />

      {/* Main Authentication Section */}
      <div
        style={{
          flexGrow: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '36px 20px',
        }}
      >
        <div
          style={{
            maxWidth: '1080px',
            width: '100%',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
            gap: '28px',
            alignItems: 'stretch',
          }}
        >
          {/* Left Column: Official Administrative Context & Demo Roles */}
          <div
            style={{
              background: '#FFFFFF',
              border: '1px solid #D7DEE5',
              borderRadius: '4px',
              padding: '30px',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 1px 3px rgba(18, 52, 90, 0.06)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#174F82', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '8px' }}>
              <ShieldCheck size={16} color="#174F82" />
              <span>STATUTORY E-GOVERNANCE PORTAL</span>
            </div>

            <h2 style={{ fontSize: '20px', fontWeight: 900, color: '#12345A', margin: '0 0 10px 0', letterSpacing: '-0.3px' }}>
              National Student Data Verification & Regulatory Gateway
            </h2>

            <p style={{ fontSize: '13px', color: '#5F6B76', lineHeight: 1.6, margin: '0 0 20px 0' }}>
              Authorised access point for AICTE regulatory reviewers, higher education officials, and participating institutions to reconcile student trajectories, verify intake allocations, and investigate inter-institutional discrepancies.
            </p>

            {/* Statutory Notice Callout */}
            <div
              style={{
                background: '#EAF2F8',
                borderLeft: '4px solid #174F82',
                padding: '12px 14px',
                borderRadius: '2px',
                fontSize: '12px',
                color: '#12345A',
                marginBottom: '20px',
              }}
            >
              <strong>Security Protocol Notice:</strong> Access is restricted to authorised personnel. Every login, submission, and resolution decision is cryptographically signed and recorded in the append-only SHA-256 audit ledger.
            </div>

            {/* Quick Demonstration Role Selector */}
            <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid #E8ECEF' }}>
              <div style={{ fontSize: '11.5px', fontWeight: 700, color: '#12345A', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: '10px' }}>
                Select Demonstration Profile (Single-Click Fill):
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => handleQuickFill('sysadmin@aicte.gov.in', 'Admin@12345')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    border: '1px solid #CBD5E1',
                    background: '#F8FAFC',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '12px',
                  }}
                  className="hover:border-blue-600 hover:bg-blue-50 transition"
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#12345A' }}>AICTE System Administrator</div>
                    <div style={{ color: '#64748B', fontSize: '11px' }}>sysadmin@aicte.gov.in &bull; Full Central Privileges</div>
                  </div>
                  <span style={{ fontSize: '10px', background: '#12345A', color: '#fff', padding: '2px 6px', borderRadius: '2px', fontWeight: 700 }}>SELECT</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickFill('reviewer@aicte.gov.in', 'Reviewer@12345')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    border: '1px solid #CBD5E1',
                    background: '#F8FAFC',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '12px',
                  }}
                  className="hover:border-blue-600 hover:bg-blue-50 transition"
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#0D7A68' }}>AICTE Regulatory Reviewer</div>
                    <div style={{ color: '#64748B', fontSize: '11px' }}>reviewer@aicte.gov.in &bull; Regulatory Inspection & Cases</div>
                  </div>
                  <span style={{ fontSize: '10px', background: '#0D7A68', color: '#fff', padding: '2px 6px', borderRadius: '2px', fontWeight: 700 }}>SELECT</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickFill('admin@apex.edu.in', 'Apex@12345')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    border: '1px solid #CBD5E1',
                    background: '#F8FAFC',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '12px',
                  }}
                  className="hover:border-blue-600 hover:bg-blue-50 transition"
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#1E40AF' }}>Apex Institute of Technology</div>
                    <div style={{ color: '#64748B', fontSize: '11px' }}>admin@apex.edu.in &bull; Institutional Tenancy Node</div>
                  </div>
                  <span style={{ fontSize: '10px', background: '#1E40AF', color: '#fff', padding: '2px 6px', borderRadius: '2px', fontWeight: 700 }}>SELECT</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickFill('admin@kaveri.edu.in', 'Kaveri@12345')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    border: '1px solid #CBD5E1',
                    background: '#F8FAFC',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '12px',
                  }}
                  className="hover:border-blue-600 hover:bg-blue-50 transition"
                >
                  <div>
                    <div style={{ fontWeight: 700, color: '#1E40AF' }}>Kaveri University</div>
                    <div style={{ color: '#64748B', fontSize: '11px' }}>admin@kaveri.edu.in &bull; University Tenancy Node</div>
                  </div>
                  <span style={{ fontSize: '10px', background: '#1E40AF', color: '#fff', padding: '2px 6px', borderRadius: '2px', fontWeight: 700 }}>SELECT</span>
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Formal Government Login Card */}
          <div
            style={{
              background: '#FFFFFF',
              border: '1px solid #D7DEE5',
              borderRadius: '4px',
              padding: '32px 30px',
              boxShadow: '0 2px 6px rgba(18, 52, 90, 0.08)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
            }}
          >
            {/* National Crest header */}
            <div style={{ textAlign: 'center', marginBottom: '22px' }}>
              <div
                style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '50%',
                  background: '#12345A',
                  color: '#FF9933',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '10px',
                  border: '2px solid #E58A24',
                }}
              >
                <Key size={26} />
              </div>

              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#12345A', margin: '0 0 4px 0' }}>
                Official Sign In
              </h3>
              <p style={{ fontSize: '12.5px', color: '#5F6B76', margin: 0 }}>
                Ministry of Education / AICTE Administrative Gateway
              </p>
            </div>

            {wasRevoked && (
              <div
                style={{
                  background: '#FEF2F2',
                  border: '1px solid #FCA5A5',
                  color: '#991B1B',
                  padding: '10px 12px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <AlertCircle size={16} />
                <span>Session revoked or expired. Please sign in again.</span>
              </div>
            )}

            {error && (
              <div
                style={{
                  background: '#FEF3F2',
                  border: '1px solid #FECDCA',
                  color: '#B42318',
                  padding: '10px 12px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 700, color: '#12345A', marginBottom: '6px' }}>
                  Official Email Address *
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
                  <input
                    type="email"
                    required
                    placeholder="official.name@domain.gov.in"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '9px 12px 9px 36px',
                      borderRadius: '4px',
                      border: '1px solid #D7DEE5',
                      fontSize: '13px',
                      background: '#FFFFFF',
                      color: '#12345A',
                    }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '22px' }}>
                <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 700, color: '#12345A', marginBottom: '6px' }}>
                  Administrative Password *
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="Enter security password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '9px 38px 9px 36px',
                      borderRadius: '4px',
                      border: '1px solid #D7DEE5',
                      fontSize: '13px',
                      background: '#FFFFFF',
                      color: '#12345A',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#94A3B8',
                      padding: '2px',
                    }}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  background: '#12345A',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '11px',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  boxShadow: '0 2px 4px rgba(18, 52, 90, 0.2)',
                }}
              >
                <span>{loading ? 'Verifying Credentials...' : 'Sign In to Portal'}</span>
                <ArrowRight size={16} />
              </button>
            </form>

            <div
              style={{
                marginTop: '22px',
                paddingTop: '16px',
                borderTop: '1px solid #E8ECEF',
                fontSize: '11px',
                color: '#718096',
                textAlign: 'center',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              <ShieldCheck size={14} color="#23834A" />
              <span>TLS 1.3 / 256-bit Authenticated Communication</span>
            </div>
          </div>
        </div>
      </div>

      {/* Persistent Footer */}
      <GovFooter />
    </div>
  );
};
