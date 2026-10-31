import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { StudentSummary, StudentTimeline } from '../types/student';
import {
  Search,
  Plus,
  Clock,
  X,
  Filter,
  AlertCircle,
  FileText,
} from 'lucide-react';

export const StudentRepository: React.FC = () => {
  const { user } = useAuth();
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProgramme, setSelectedProgramme] = useState<string>('');
  const [programmes, setProgrammes] = useState<any[]>([]);

  // Timeline Drawer State
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [timelineData, setTimelineData] = useState<StudentTimeline | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Register Modal State
  const [registerOpen, setRegisterOpen] = useState(false);
  const [formData, setFormData] = useState({
    institution_student_id: '',
    full_name: '',
    programme_id: '',
    academic_year: '2024-25',
    admission_date: '2024-08-01',
    apaar_id: '',
    date_of_birth: '2006-05-15',
    gender: 'M',
    admission_category: 'REGULAR',
    supernumerary_status: false,
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Fetch Programmes for dropdown
  useEffect(() => {
    const fetchProgrammes = async () => {
      try {
        if (user?.institution_id) {
          const res = await api.get(`/institutions/${user.institution_id}/programmes`);
          setProgrammes(res.data);
          if (res.data.length > 0) {
            setFormData((prev) => ({ ...prev, programme_id: res.data[0].id }));
          }
        }
      } catch (err) {
        console.error('Failed to load programmes', err);
      }
    };
    fetchProgrammes();
  }, [user]);

  // Fetch Students list
  const fetchStudents = async () => {
    setLoading(true);
    try {
      const res = await api.get('/students', {
        params: {
          search: searchTerm || undefined,
          programme_id: selectedProgramme || undefined,
        },
      });
      setStudents(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      console.error('Failed to load students', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, [searchTerm, selectedProgramme]);

  // View Student Timeline
  const handleViewTimeline = async (studentId: string) => {
    setSelectedStudentId(studentId);
    setTimelineLoading(true);
    setTimelineData(null);
    try {
      const res = await api.get(`/students/${studentId}/timeline`);
      setTimelineData(res.data);
    } catch (err) {
      console.error('Failed to load timeline', err);
    } finally {
      setTimelineLoading(false);
    }
  };

  // Submit Register Student
  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSubmitting(true);
    try {
      await api.post('/students', formData);
      setRegisterOpen(false);
      fetchStudents();
      setFormData((prev) => ({
        ...prev,
        institution_student_id: '',
        full_name: '',
        apaar_id: '',
      }));
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to register student record.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const getIdentityBadge = (status: string) => {
    switch (status) {
      case 'FORMAT_VALID':
        return <span className="gov-badge gov-badge-verified">FORMAT VALID (UNVERIFIED)</span>;
      case 'MISSING_APAAR':
        return <span className="gov-badge gov-badge-warning">MISSING APAAR</span>;
      case 'EXTERNALLY_VERIFIED':
        return <span className="gov-badge gov-badge-info">ADAPTER VERIFIED</span>;
      case 'INVALID_FORMAT':
        return <span className="gov-badge gov-badge-danger">INVALID FORMAT</span>;
      default:
        return <span className="gov-badge gov-badge-neutral">{status}</span>;
    }
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* Page Title & Context Header */}
      <div
        style={{
          borderBottom: '2px solid #D7DEE5',
          paddingBottom: '14px',
          marginBottom: '18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#174F82', fontSize: '11.5px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            <FileText size={14} />
            <span>INSTITUTIONAL REGISTRY & LONGITUDINAL CENSUS</span>
          </div>
          <h1 style={{ fontSize: '22px', fontWeight: 900, color: '#12345A', margin: '3px 0 4px 0', letterSpacing: '-0.3px' }}>
            National Student Repository
          </h1>
          <p style={{ fontSize: '13px', color: '#5F6B76', margin: 0 }}>
            Authoritative student-level enrollment records, DPDPA-compliant masked APAAR identifiers, admission episodes, and annual roster observations.
          </p>
        </div>

        {user?.role === 'INSTITUTION_ADMIN' && (
          <button
            onClick={() => setRegisterOpen(true)}
            className="gov-btn-primary"
            style={{ padding: '8px 14px' }}
          >
            <Plus size={15} />
            <span>Register Student Record</span>
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div
        style={{
          background: '#FFFFFF',
          border: '1px solid #D7DEE5',
          borderRadius: '4px',
          padding: '12px 16px',
          marginBottom: '18px',
          display: 'flex',
          gap: '12px',
          alignItems: 'center',
          flexWrap: 'wrap',
          boxShadow: 'var(--gov-shadow-sm)',
        }}
      >
        <div style={{ position: 'relative', flexGrow: 1, minWidth: '280px' }}>
          <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#718096' }} />
          <input
            type="text"
            placeholder="Search by student name, roll number, or masked APAAR..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="gov-input"
            style={{ paddingLeft: '34px' }}
          />
        </div>

        {programmes.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Filter size={15} color="#5F6B76" />
            <select
              value={selectedProgramme}
              onChange={(e) => setSelectedProgramme(e.target.value)}
              className="gov-input"
              style={{ width: 'auto', minWidth: '220px' }}
            >
              <option value="">All Academic Programmes</option>
              {programmes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.programme_name} ({p.programme_code})
                </option>
              ))}
            </select>
          </div>
        )}

        <div style={{ fontSize: '12px', color: '#5F6B76', marginLeft: 'auto' }}>
          Total Registered Records: <strong style={{ color: '#12345A' }}>{total}</strong>
        </div>
      </div>

      {/* Main Student Records Table */}
      <div className="gov-table-container">
        <div className="gov-table-header">
          <div style={{ fontWeight: 800, fontSize: '13px', color: '#12345A' }}>
            Registered Student Census ({total} records)
          </div>
          <div style={{ fontSize: '11px', color: '#5F6B76' }}>
            Data Privacy Notice: Full 12-digit APAAR references are cryptographically masked in accordance with DPDPA 2023.
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '36px', textAlign: 'center', color: '#718096', fontSize: '13px' }}>
            Querying student repository from database...
          </div>
        ) : students.length === 0 ? (
          <div style={{ padding: '36px', textAlign: 'center', color: '#718096', fontSize: '13px' }}>
            No matching student records found.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="gov-table">
              <thead>
                <tr>
                  <th style={{ width: '130px' }}>Roll Number</th>
                  <th>Student Full Name</th>
                  <th>Masked APAAR Reference</th>
                  <th>Institution / Jurisdiction</th>
                  <th>Academic Programme</th>
                  <th style={{ textAlign: 'center' }}>Enrollment Status</th>
                  <th style={{ textAlign: 'center' }}>Identity Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#12345A' }}>
                      {s.institution_student_id}
                    </td>
                    <td style={{ fontWeight: 700, color: '#1A2530' }}>
                      {s.full_name}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#174F82' }}>
                      {s.masked_apaar_reference || (
                        <span style={{ color: '#B7791F', fontStyle: 'italic' }}>Pending APAAR</span>
                      )}
                    </td>
                    <td style={{ color: '#4A5568', fontSize: '12.5px' }}>
                      {s.institution_name || 'Apex Institute of Technology'}
                    </td>
                    <td style={{ color: '#4A5568', fontSize: '12.5px' }}>
                      {s.programme_name} ({s.programme_code})
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span
                        className={`gov-badge ${
                          s.status === 'ACTIVE' || s.status === 'ENROLLED'
                            ? 'gov-badge-verified'
                            : s.status === 'WITHDRAWN'
                            ? 'gov-badge-danger'
                            : 'gov-badge-neutral'
                        }`}
                      >
                        {s.status}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {getIdentityBadge(s.identity_status)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => handleViewTimeline(s.id)}
                        style={{
                          background: '#EAF2F8',
                          color: '#174F82',
                          border: '1px solid #BCD4E6',
                          borderRadius: '3px',
                          padding: '4px 8px',
                          fontSize: '11.5px',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                        title="Inspect longitudinal observations and admission history"
                      >
                        <Clock size={12} />
                        <span>Trajectory</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Longitudinal Trajectory Drawer */}
      {selectedStudentId && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(11, 31, 54, 0.6)',
            display: 'flex',
            justifyContent: 'flex-end',
            zIndex: 100,
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '560px',
              background: '#FFFFFF',
              height: '100vh',
              overflowY: 'auto',
              boxShadow: '-4px 0 16px rgba(18, 52, 90, 0.2)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Drawer Header */}
            <div
              style={{
                padding: '16px 20px',
                background: '#12345A',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ fontSize: '11px', color: '#E58A24', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  STATUTORY AUDIT LINEAGE
                </div>
                <h3 style={{ fontSize: '16px', fontWeight: 800, margin: '2px 0 0 0' }}>
                  Student Trajectory History
                </h3>
              </div>
              <button
                onClick={() => setSelectedStudentId(null)}
                style={{ background: 'none', border: 'none', color: '#FFFFFF', cursor: 'pointer', padding: '4px' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Drawer Content */}
            <div style={{ padding: '20px', flexGrow: 1 }}>
              {timelineLoading ? (
                <div style={{ padding: '36px', textAlign: 'center', color: '#718096' }}>
                  Loading longitudinal history...
                </div>
              ) : timelineData ? (
                <div>
                  {/* Identity Summary Card */}
                  <div
                    style={{
                      background: '#F8FAFC',
                      border: '1px solid #D7DEE5',
                      borderRadius: '4px',
                      padding: '14px',
                      marginBottom: '20px',
                    }}
                  >
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#12345A' }}>
                      {timelineData.identity.full_name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#5F6B76', marginTop: '2px' }}>
                      Internal UUID: <span style={{ fontFamily: 'var(--font-mono)' }}>{timelineData.identity.internal_student_uuid.slice(0, 16)}...</span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                      {getIdentityBadge(timelineData.identity.identity_status)}
                      <span className="gov-badge gov-badge-info">
                        MASKED: {timelineData.identity.masked_apaar || 'NO-APAAR'}
                      </span>
                    </div>
                  </div>

                  {/* Institutional Enrolment History */}
                  {timelineData.institutions_enrolled && timelineData.institutions_enrolled.length > 0 && (
                    <div style={{ marginBottom: '20px' }}>
                      <div style={{ fontWeight: 800, fontSize: '13px', color: '#12345A', marginBottom: '8px' }}>
                        Institutional Enrolment Records ({timelineData.institutions_enrolled.length})
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {timelineData.institutions_enrolled.map((inst, idx) => (
                          <div key={idx} style={{ background: '#F8FAFC', border: '1px solid #D7DEE5', padding: '10px 14px', borderRadius: '2px' }}>
                            <div style={{ fontWeight: 700, color: '#12345A', fontSize: '13px' }}>
                              {inst.institution_name} ({inst.institution_code})
                            </div>
                            <div style={{ fontSize: '12px', color: '#5F6B76', marginTop: '2px' }}>
                              Programme: {inst.programme_name} &bull; Reg ID: {inst.student_id} &bull; Status: <span className="gov-badge gov-badge-verified">{inst.status}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Longitudinal Academic Events */}
                  <div style={{ fontWeight: 800, fontSize: '13px', color: '#12345A', marginBottom: '12px' }}>
                    Longitudinal Trajectory Ledger ({timelineData.timeline ? timelineData.timeline.length : 0} events)
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px' }}>
                    {timelineData.timeline && timelineData.timeline.map((ev, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: '#FFFFFF',
                          border: '1px solid #D7DEE5',
                          borderLeft: ev.type === 'ADMISSION' ? '4px solid #23834A' : ev.type === 'TRANSFER' ? '4px solid #E58A24' : '4px solid #174F82',
                          borderRadius: '2px',
                          padding: '10px 14px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 800, color: '#12345A', fontSize: '13px' }}>
                            {ev.type}: {ev.academic_year}
                          </span>
                          <span className={ev.type === 'ADMISSION' ? 'gov-badge gov-badge-verified' : ev.type === 'TRANSFER' ? 'gov-badge gov-badge-warning' : 'gov-badge gov-badge-info'}>
                            {ev.status || ev.category || ev.type}
                          </span>
                        </div>
                        <div style={{ fontSize: '12px', color: '#202B36', marginTop: '4px' }}>
                          {ev.description} {ev.programme ? `— ${ev.programme}` : ''} {ev.institution ? `(${ev.institution})` : ''}
                        </div>
                        {(ev.date || ev.timestamp) && (
                          <div style={{ fontSize: '11px', color: '#5F6B76', marginTop: '2px' }}>
                            Recorded: {new Date(ev.date || ev.timestamp || '').toLocaleDateString('en-IN')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div style={{ padding: '36px', textAlign: 'center', color: '#718096' }}>
                  No timeline data available.
                </div>
              )}
            </div>

            {/* Drawer Footer */}
            <div style={{ padding: '12px 20px', borderTop: '1px solid #D7DEE5', background: '#F8FAFC', textAlign: 'right' }}>
              <button
                onClick={() => setSelectedStudentId(null)}
                className="gov-btn-secondary"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Register Student Record */}
      {registerOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(11, 31, 54, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '16px',
          }}
        >
          <div
            style={{
              background: '#FFFFFF',
              borderRadius: '4px',
              maxWidth: '540px',
              width: '100%',
              boxShadow: 'var(--gov-shadow-lg)',
              overflow: 'hidden',
              border: '1px solid #D7DEE5',
            }}
          >
            <div
              style={{
                padding: '14px 20px',
                background: '#12345A',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <h3 style={{ fontSize: '15px', fontWeight: 800, margin: 0 }}>
                Register Institutional Student Record
              </h3>
              <button
                onClick={() => setRegisterOpen(false)}
                style={{ background: 'none', border: 'none', color: '#FFFFFF', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleRegisterSubmit} style={{ padding: '20px' }}>
              {formError && (
                <div className="gov-notice-warning" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <AlertCircle size={16} />
                  <span>{formError}</span>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#12345A', marginBottom: '4px' }}>
                    Roll Number / Student ID *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 24CSE001"
                    value={formData.institution_student_id}
                    onChange={(e) => setFormData({ ...formData, institution_student_id: e.target.value })}
                    className="gov-input"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#12345A', marginBottom: '4px' }}>
                    Student Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ramesh Sharma"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    className="gov-input"
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#12345A', marginBottom: '4px' }}>
                    APAAR ID (12-Digit Reference)
                  </label>
                  <input
                    type="text"
                    maxLength={12}
                    placeholder="e.g. 990000000001"
                    value={formData.apaar_id}
                    onChange={(e) => setFormData({ ...formData, apaar_id: e.target.value })}
                    className="gov-input"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#12345A', marginBottom: '4px' }}>
                    Academic Programme *
                  </label>
                  <select
                    value={formData.programme_id}
                    onChange={(e) => setFormData({ ...formData, programme_id: e.target.value })}
                    className="gov-input"
                    required
                  >
                    {programmes.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.programme_name} ({p.programme_code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px', borderTop: '1px solid #E8ECEF', paddingTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setRegisterOpen(false)}
                  className="gov-btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="gov-btn-primary"
                >
                  {formSubmitting ? 'Recording...' : 'Save Student Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
