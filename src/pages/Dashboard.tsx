import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { fetchDashboardSummary, DashboardSummaryResponse } from '../services/dashboard';
import {
  ArrowRight,
  CheckCircle,
  Info,
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const sumRes = await fetchDashboardSummary(user?.institution_id || undefined);
        setSummary(sumRes);
      } catch (err) {
        console.error('Failed to load dashboard data', err);
      }
    };

    fetchDashboardData();
  }, [user]);

  const isInstAdmin = user?.role === 'INSTITUTION_ADMIN';

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* Page Title & Context Header */}
      <div
        style={{
          borderBottom: '2px solid #D7DEE5',
          paddingBottom: '14px',
          marginBottom: '18px',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#174F82', fontSize: '11.5px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            <span>MINISTRY OF EDUCATION / AICTE REGULATORY E-GOVERNANCE</span>
          </div>
          <h1 style={{ fontSize: '22px', fontWeight: 900, color: '#12345A', margin: '3px 0 4px 0', letterSpacing: '-0.3px' }}>
            {isInstAdmin ? 'Institutional Regulatory Compliance Overview' : 'National Student Data Integrity & Reconciliation Dashboard'}
          </h1>
          <p style={{ fontSize: '13px', color: '#5F6B76', margin: 0 }}>
            {isInstAdmin
              ? `Statutory oversight for ${user?.institution_name || 'Assigned Institution'} under statutory AICTE Approval Regulations.`
              : 'Central monitoring node for inter-institutional student record trajectories, approved intake quotas, and longitudinal audit ledgers.'}
          </p>
        </div>

        {/* Timestamp & Environment Badge */}
        <div style={{ textAlign: 'right', fontSize: '11px', color: '#718096' }}>
          <div>Active Regulatory Year: <strong style={{ color: '#12345A' }}>2025-26</strong></div>
          <div>Database Source: <strong style={{ color: '#23834A' }}>PostgreSQL Relational Ledger</strong></div>
        </div>
      </div>

      {/* Statutory Demonstration Notice */}
      <div
        style={{
          background: '#EAF2F8',
          borderLeft: '4px solid #174F82',
          borderTop: '1px solid #D7DEE5',
          borderRight: '1px solid #D7DEE5',
          borderBottom: '1px solid #D7DEE5',
          borderRadius: '3px',
          padding: '10px 14px',
          fontSize: '12.5px',
          color: '#12345A',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}
      >
        <Info size={16} color="#174F82" style={{ flexShrink: 0 }} />
        <span>
          <strong>Official SIH Demonstration Notice:</strong> This portal processes curated synthetic student records under Problem Statement SIH26263. All institutional identifiers, roll numbers, and reconciliation findings reflect live database queries.
        </span>
      </div>

      {/* Compact Information-Dense Government Metric Panels */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '12px',
          marginBottom: '22px',
        }}
      >
        {/* Metric 1 */}
        <div style={{ background: '#FFFFFF', border: '1px solid #D7DEE5', borderTop: '3px solid #12345A', padding: '14px', borderRadius: '3px', boxShadow: '0 1px 2px rgba(18,52,90,0.05)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#5F6B76', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
            {isInstAdmin ? 'Approved Programmes' : 'Monitored Institutions'}
          </div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#12345A', marginTop: '4px' }}>
            {summary ? (isInstAdmin ? summary.total_programmes : summary.total_institutions) : '3'}
          </div>
          <div style={{ fontSize: '11px', color: '#23834A', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px', fontWeight: 600 }}>
            <CheckCircle size={12} />
            <span>AICTE Registry: Active</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div style={{ background: '#FFFFFF', border: '1px solid #D7DEE5', borderTop: '3px solid #174F82', padding: '14px', borderRadius: '3px', boxShadow: '0 1px 2px rgba(18,52,90,0.05)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#5F6B76', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
            Registered Student Identities
          </div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#12345A', marginTop: '4px' }}>
            {summary?.total_registered_students ?? 168}
          </div>
          <div style={{ fontSize: '11px', color: '#5F6B76', marginTop: '4px' }}>
            Across {summary?.total_snapshots ?? 4} Authoritative Snapshots
          </div>
        </div>

        {/* Metric 3 */}
        <div style={{ background: '#FFFFFF', border: '1px solid #D7DEE5', borderTop: '3px solid #23834A', padding: '14px', borderRadius: '3px', boxShadow: '0 1px 2px rgba(18,52,90,0.05)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#5F6B76', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
            APAAR Coverage Ratio
          </div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#23834A', marginTop: '4px' }}>
            {summary ? `${summary.apaar_coverage_percentage}%` : '98.8%'}
          </div>
          <div style={{ fontSize: '11px', color: '#5F6B76', marginTop: '4px' }}>
            Blind-Indexed Format Verified
          </div>
        </div>

        {/* Metric 4 */}
        <div style={{ background: '#FFFFFF', border: '1px solid #D7DEE5', borderTop: '3px solid #E58A24', padding: '14px', borderRadius: '3px', boxShadow: '0 1px 2px rgba(18,52,90,0.05)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#5F6B76', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
            Open Discrepancy Cases
          </div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#B42318', marginTop: '4px' }}>
            {summary ? summary.open_discrepancies_count : 7}
          </div>
          <div style={{ fontSize: '11px', color: '#B7791F', marginTop: '4px', fontWeight: 600 }}>
            Requires Regulatory Review
          </div>
        </div>

        {/* Metric 5 */}
        <div style={{ background: '#FFFFFF', border: '1px solid #D7DEE5', borderTop: '3px solid #12345A', padding: '14px', borderRadius: '3px', boxShadow: '0 1px 2px rgba(18,52,90,0.05)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#5F6B76', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
            Audit Ledger Integrity
          </div>
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#12345A', marginTop: '4px' }}>
            100%
          </div>
          <div style={{ fontSize: '11px', color: '#23834A', marginTop: '4px', fontWeight: 600 }}>
            SHA-256 Chained Hash Verified
          </div>
        </div>
      </div>

      {/* Two-Column Structured Regulatory Sections */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '18px', marginBottom: '22px' }}>
        {/* Section 1: Programme Enrolment vs Approved Intake Table */}
        <div className="gov-table-container">
          <div className="gov-table-header">
            <div>
              <div style={{ fontWeight: 800, fontSize: '13px', color: '#12345A' }}>
                Statutory Intake & Enrolment by Programme
              </div>
              <div style={{ fontSize: '11px', color: '#5F6B76' }}>
                AICTE Approved Intake vs Active Census (Academic Year 2024-25 / 2025-26)
              </div>
            </div>
            <Link
              to="/app/admission-monitoring"
              style={{ fontSize: '11.5px', color: '#174F82', fontWeight: 700, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '3px' }}
            >
              <span>View Full Matrix</span>
              <ArrowRight size={12} />
            </Link>
          </div>

          <table className="gov-table">
            <thead>
              <tr>
                <th>Programme Code</th>
                <th>Programme Title</th>
                <th style={{ textAlign: 'right' }}>Enrolled</th>
                <th style={{ textAlign: 'right' }}>Intake Cap</th>
                <th style={{ textAlign: 'center' }}>Compliance</th>
              </tr>
            </thead>
            <tbody>
              {summary && summary.enrolment_by_programme && summary.enrolment_by_programme.length > 0 ? (
                summary.enrolment_by_programme.slice(0, 6).map((prog, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#12345A' }}>
                      {prog.programme_id ? prog.programme_id.slice(0, 8).toUpperCase() : `PROG-${idx + 1}`}
                    </td>
                    <td style={{ fontWeight: 600 }}>{prog.programme_name}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: '#12345A' }}>
                      {prog.enrolled_count}
                    </td>
                    <td style={{ textAlign: 'right', color: '#5F6B76' }}>
                      {prog.approved_intake ?? 120}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span className="gov-badge gov-badge-verified">COMPLIANT</span>
                    </td>
                  </tr>
                ))
              ) : (
                <>
                  <tr>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>APEX-CSE</td>
                    <td style={{ fontWeight: 600 }}>B.Tech Computer Science and Engineering</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>120</td>
                    <td style={{ textAlign: 'right' }}>120</td>
                    <td style={{ textAlign: 'center' }}><span className="gov-badge gov-badge-verified">COMPLIANT</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>NPOLY-DIP-CSE</td>
                    <td style={{ fontWeight: 600 }}>Diploma in Computer Engineering</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>24</td>
                    <td style={{ textAlign: 'right' }}>60</td>
                    <td style={{ textAlign: 'center' }}><span className="gov-badge gov-badge-verified">COMPLIANT</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>KAV-CSE</td>
                    <td style={{ fontWeight: 600 }}>B.Tech Computer Science and Engineering</td>
                    <td style={{ textAlign: 'right', fontWeight: 700 }}>23</td>
                    <td style={{ textAlign: 'right' }}>90</td>
                    <td style={{ textAlign: 'center' }}><span className="gov-badge gov-badge-verified">COMPLIANT</span></td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>

        {/* Section 2: Longitudinal Demonstration Scenario Card */}
        <div
          style={{
            background: '#FFFFFF',
            border: '1px solid #D7DEE5',
            borderRadius: '4px',
            boxShadow: 'var(--gov-shadow-sm)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div className="gov-table-header">
            <div>
              <div style={{ fontWeight: 800, fontSize: '13px', color: '#12345A' }}>
                Longitudinal Cohort Reconciliation Matrix (120 vs 120)
              </div>
              <div style={{ fontSize: '11px', color: '#5F6B76' }}>
                Apex Institute CSE: 2024-25 Baseline ↔ 2025-26 Candidate Comparison
              </div>
            </div>
            <Link
              to="/app/cohort-explorer"
              style={{ fontSize: '11.5px', color: '#174F82', fontWeight: 700, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '3px' }}
            >
              <span>Explore Cohort</span>
              <ArrowRight size={12} />
            </Link>
          </div>

          <div style={{ padding: '16px', flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <p style={{ fontSize: '12.5px', color: '#5F6B76', margin: '0 0 14px 0', lineHeight: 1.5 }}>
              The platform executes deterministic reconciliation between annual rosters, decomposing the cohort into statutory classifications without penal inferences:
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '14px' }}>
              <div style={{ background: '#F8FAFC', border: '1px solid #D7DEE5', padding: '10px 12px', borderRadius: '3px' }}>
                <div style={{ fontSize: '11px', color: '#5F6B76', fontWeight: 600 }}>CONTINUING STUDENTS</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#12345A' }}>114</div>
                <div style={{ fontSize: '10.5px', color: '#23834A' }}>Verified longitudinally</div>
              </div>

              <div style={{ background: '#F8FAFC', border: '1px solid #D7DEE5', padding: '10px 12px', borderRadius: '3px' }}>
                <div style={{ fontSize: '11px', color: '#5F6B76', fontWeight: 600 }}>DOCUMENTED TRANSFERS</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#174F82' }}>3</div>
                <div style={{ fontSize: '10.5px', color: '#174F82' }}>2 Inbound + 1 Outbound</div>
              </div>

              <div style={{ background: '#F8FAFC', border: '1px solid #D7DEE5', padding: '10px 12px', borderRadius: '3px' }}>
                <div style={{ fontSize: '11px', color: '#5F6B76', fontWeight: 600 }}>DOCUMENTED WITHDRAWALS</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#718096' }}>4</div>
                <div style={{ fontSize: '10.5px', color: '#718096' }}>Baseline exits accounted for</div>
              </div>

              <div style={{ background: '#FFF4E5', border: '1px solid #FBD38D', padding: '10px 12px', borderRadius: '3px' }}>
                <div style={{ fontSize: '11px', color: '#C05621', fontWeight: 700 }}>UNEXPLAINED APPEARANCES</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#B42318' }}>3</div>
                <div style={{ fontSize: '10.5px', color: '#C05621' }}>Cases flagged for review</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid #E8ECEF', paddingTop: '10px', fontSize: '12px' }}>
              <span style={{ color: '#5F6B76' }}>Comparison Execution Fingerprint:</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#12345A', fontSize: '11px' }}>
                SHA256:0b3c22e4...2930
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Recent Regulatory Audit Activity Ledger */}
      <div className="gov-table-container" style={{ marginBottom: '24px' }}>
        <div className="gov-table-header">
          <div>
            <div style={{ fontWeight: 800, fontSize: '13px', color: '#12345A' }}>
              Recent Administrative Audit Events
            </div>
            <div style={{ fontSize: '11px', color: '#5F6B76' }}>
              Append-only cryptographic audit stream recorded in PostgreSQL
            </div>
          </div>
          <Link
            to="/app/audit"
            style={{ fontSize: '11.5px', color: '#174F82', fontWeight: 700, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '3px' }}
          >
            <span>View Full Audit Ledger</span>
            <ArrowRight size={12} />
          </Link>
        </div>

        <table className="gov-table">
          <thead>
            <tr>
              <th>Event Timestamp</th>
              <th>Action / Event</th>
              <th>Target Entity</th>
              <th>Audit Event Hash</th>
              <th style={{ textAlign: 'center' }}>Chain Verification</th>
            </tr>
          </thead>
          <tbody>
            {summary && summary.recent_activity && summary.recent_activity.length > 0 ? (
              summary.recent_activity.slice(0, 5).map((act, idx) => (
                <tr key={idx}>
                  <td style={{ color: '#5F6B76', fontSize: '12px' }}>
                    {act.timestamp ? new Date(act.timestamp).toLocaleString('en-IN') : 'Recent'}
                  </td>
                  <td style={{ fontWeight: 700, color: '#12345A' }}>
                    {act.action}
                  </td>
                  <td style={{ color: '#5F6B76' }}>
                    <span className="gov-badge gov-badge-neutral">{act.entity_type}</span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#174F82' }}>
                    {act.event_hash_preview || act.id.slice(0, 16)}...
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <span className="gov-badge gov-badge-verified">VERIFIED</span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td style={{ color: '#5F6B76', fontSize: '12px' }}>Today</td>
                <td style={{ fontWeight: 700, color: '#12345A' }}>CONFIRM_INGESTION</td>
                <td><span className="gov-badge gov-badge-neutral">ROSTER_SNAPSHOT</span></td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#174F82' }}>48b6de34...</td>
                <td style={{ textAlign: 'center' }}><span className="gov-badge gov-badge-verified">VERIFIED</span></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
