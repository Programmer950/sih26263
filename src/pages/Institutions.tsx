import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api, { extractErrorMessage } from '../services/api';
import { InstitutionSummary, ProgrammeSummary } from '../types/auth';
import {
  ShieldCheck,
  MapPin,
  Mail,
  Layers,
  Search,
  Plus,
  ChevronDown,
  ChevronUp,
  Building2,
  BookOpen,
  CheckCircle,
  X,
  AlertCircle,
} from 'lucide-react';

export const Institutions: React.FC = () => {
  const { user } = useAuth();
  const [institutions, setInstitutions] = useState<InstitutionSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Expandable programme drawer per institution
  const [expandedInstId, setExpandedInstId] = useState<string | null>(null);
  const [instProgrammes, setInstProgrammes] = useState<Record<string, ProgrammeSummary[]>>({});
  const [loadingProgrammes, setLoadingProgrammes] = useState<Record<string, boolean>>({});

  // Modals
  const [showInstModal, setShowInstModal] = useState(false);
  const [showProgModal, setShowProgModal] = useState(false);
  const [targetInstForProg, setTargetInstForProg] = useState<InstitutionSummary | null>(null);

  // Form State: Register Institution
  const [newInst, setNewInst] = useState({
    institution_code: '',
    name: '',
    category: 'ENGINEERING',
    state: '',
    district: '',
    pincode: '',
    address: '',
    contact_email: '',
  });

  // Form State: Add Programme
  const [newProg, setNewProg] = useState({
    programme_code: '',
    programme_name: '',
    qualification_level: 'UG',
    duration_years: 4,
    approved_intake: 120,
    academic_year: '2024-25',
  });

  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchInstitutions = async () => {
    setLoading(true);
    try {
      const res = await api.get('/institutions', {
        params: { search: searchTerm || undefined },
      });
      const items = res.data.items || [];
      setInstitutions(items);
      setTotal(res.data.total ?? items.length);
    } catch (err) {
      console.error('Failed to load institutions', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInstitutions();
  }, [searchTerm]);

  const fetchProgrammesForInst = async (instId: string) => {
    setLoadingProgrammes((prev) => ({ ...prev, [instId]: true }));
    try {
      const res = await api.get(`/institutions/${instId}/programmes`);
      const progs = res.data.items || res.data || [];
      setInstProgrammes((prev) => ({ ...prev, [instId]: progs }));
    } catch (err) {
      console.error(`Failed to load programmes for ${instId}:`, err);
    } finally {
      setLoadingProgrammes((prev) => ({ ...prev, [instId]: false }));
    }
  };

  const toggleExpand = (instId: string) => {
    if (expandedInstId === instId) {
      setExpandedInstId(null);
    } else {
      setExpandedInstId(instId);
      if (!instProgrammes[instId]) {
        fetchProgrammesForInst(instId);
      }
    }
  };

  const handleCreateInstitution = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);
    setIsSubmitting(true);
    try {
      await api.post('/institutions', {
        institution_code: newInst.institution_code.trim().toUpperCase(),
        name: newInst.name.trim(),
        category: newInst.category,
        state: newInst.state.trim(),
        district: newInst.district.trim(),
        pincode: newInst.pincode.trim() || undefined,
        address: newInst.address.trim() || undefined,
        contact_email: newInst.contact_email.trim() || undefined,
      });

      setFormSuccess(`Institution '${newInst.name}' registered successfully.`);
      setNewInst({
        institution_code: '',
        name: '',
        category: 'ENGINEERING',
        state: '',
        district: '',
        pincode: '',
        address: '',
        contact_email: '',
      });
      setTimeout(() => {
        setShowInstModal(false);
        setFormSuccess(null);
      }, 1200);
      fetchInstitutions();
    } catch (err: any) {
      setFormError(extractErrorMessage(err, 'Failed to register institution.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenAddProg = (inst: InstitutionSummary) => {
    setTargetInstForProg(inst);
    setFormError(null);
    setFormSuccess(null);
    setNewProg({
      programme_code: '',
      programme_name: '',
      qualification_level: inst.category === 'POLYTECHNIC' ? 'DIPLOMA' : 'UG',
      duration_years: inst.category === 'POLYTECHNIC' ? 3 : 4,
      approved_intake: 120,
      academic_year: '2024-25',
    });
    setShowProgModal(true);
  };

  const handleCreateProgramme = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetInstForProg) return;

    setFormError(null);
    setFormSuccess(null);
    setIsSubmitting(true);
    try {
      // 1. Create Programme
      const progRes = await api.post(`/institutions/${targetInstForProg.id}/programmes`, {
        programme_code: newProg.programme_code.trim().toUpperCase(),
        programme_name: newProg.programme_name.trim(),
        qualification_level: newProg.qualification_level,
        duration_years: Number(newProg.duration_years),
      });

      const progId = progRes.data.id;

      // 2. Add approved intake configuration if specified
      if (newProg.approved_intake > 0 && progId) {
        try {
          const yearStart = parseInt(newProg.academic_year.split('-')[0]) || 2024;
          await api.post(`/institutions/${targetInstForProg.id}/programmes/${progId}/approval-configs`, {
            academic_year: newProg.academic_year,
            approved_intake: Number(newProg.approved_intake),
            supernumerary_quota_percentage: 15.0,
            lateral_entry_quota_percentage: 10.0,
            approval_reference: `AICTE-${newProg.academic_year}-${targetInstForProg.institution_code}-${newProg.programme_code.trim().toUpperCase()}`,
            effective_from: `${yearStart}-06-01`,
            effective_to: `${yearStart + 1}-05-31`,
          });
        } catch (cfgErr) {
          console.warn('Programme intake config optional step returned:', cfgErr);
        }
      }

      setFormSuccess(`Programme '${newProg.programme_name}' added successfully.`);
      setTimeout(() => {
        setShowProgModal(false);
        setFormSuccess(null);
      }, 1200);

      // Refresh programmes and list
      fetchProgrammesForInst(targetInstForProg.id);
      fetchInstitutions();
    } catch (err: any) {
      setFormError(extractErrorMessage(err, 'Failed to create programme.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const isInstAdmin = user?.role === 'INSTITUTION_ADMIN';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Title & Actions */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#D7DEE5] gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="gov-badge gov-badge-info">
                Institutional Registry & Programme Catalogue
              </span>
              <span className="text-[11px] text-[#5F6B76] font-mono">Module 2 — Statutory Institution Profiles</span>
            </div>
            <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
              Institution & Programme Management / संस्थान एवं पाठ्यक्रम प्रबंधन
            </h1>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Structured institutional registry, approved programme capacities, and academic approval configurations required for student submissions.
            </p>
          </div>

          {!isInstAdmin && (
            <button
              onClick={() => {
                setFormError(null);
                setFormSuccess(null);
                setShowInstModal(true);
              }}
              className="gov-btn-primary text-xs py-2 px-4 flex items-center gap-1.5 shrink-0"
            >
              <Plus size={14} />
              <span>Register Institution</span>
            </button>
          )}
        </div>

        {/* Tenancy Notice for Institution Admins */}
        {isInstAdmin && (
          <div className="mt-4 p-3 bg-[#EAF2F8] border border-[#CBD7E3] rounded text-xs text-[#12345A] flex items-center gap-2.5">
            <ShieldCheck size={18} className="text-[#174F82] shrink-0" />
            <span>
              <strong>Tenant Isolation Active:</strong> As an Institution Administrator, your view and operations are strictly scoped to <strong>{user?.institution_name}</strong>. Attempts to query external institutions are rejected by the backend.
            </span>
          </div>
        )}
      </div>

      {/* Search Bar for Reviewers & Admins */}
      {!isInstAdmin && (
        <div className="bg-white border border-[#D7DEE5] rounded p-4 shadow-sm flex items-center justify-between">
          <div className="relative w-full max-w-md">
            <Search size={14} className="absolute left-3 top-2.5 text-[#5F6B76]" />
            <input
              type="text"
              placeholder="Search by institution code, name, or state..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="gov-input pl-8 text-xs w-full"
            />
          </div>
          <div className="text-xs text-[#5F6B76] font-mono">
            Total Monitored: <strong className="text-[#12345A]">{total}</strong>
          </div>
        </div>
      )}

      {/* Table Card */}
      <div className="gov-table-container">
        <div className="p-4 border-b border-[#D7DEE5] flex items-center justify-between bg-[#F4F6F8]">
          <div className="font-bold text-xs uppercase tracking-wider text-[#12345A]">
            Registered Institutions ({total})
          </div>
          <div className="text-[11px] text-[#5F6B76] font-mono">
            Source: PostgreSQL Relational Database
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-[#5F6B76] text-xs">Loading institutions from database...</div>
        ) : institutions.length === 0 ? (
          <div className="p-12 text-center">
            <Building2 size={40} className="text-[#8C9BA8] mx-auto mb-3" />
            <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide mb-1">
              No Institutions Registered
            </h3>
            <p className="text-xs text-[#5F6B76] max-w-md mx-auto mb-4">
              Before uploading student CSV rosters in Data Submissions, register your institution and approved programmes.
            </p>
            {!isInstAdmin && (
              <button
                onClick={() => {
                  setFormError(null);
                  setFormSuccess(null);
                  setShowInstModal(true);
                }}
                className="gov-btn-primary text-xs py-2 px-4 inline-flex items-center gap-1.5"
              >
                <Plus size={14} />
                <span>Register First Institution</span>
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="gov-table w-full">
              <thead>
                <tr>
                  <th className="w-10 text-center"></th>
                  <th>Code</th>
                  <th>Institution Name</th>
                  <th>Category</th>
                  <th>Location</th>
                  <th>Programmes</th>
                  <th>Approval Status</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {institutions.map((inst) => {
                  const isExpanded = expandedInstId === inst.id;
                  const progs = instProgrammes[inst.id] || [];
                  const isProgLoading = loadingProgrammes[inst.id];

                  return (
                    <React.Fragment key={inst.id}>
                      <tr className={isExpanded ? 'bg-[#F4F6F8]' : ''}>
                        <td className="text-center">
                          <button
                            onClick={() => toggleExpand(inst.id)}
                            className="text-[#5F6B76] hover:text-[#12345A] p-1"
                            title="View Programmes"
                          >
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>
                        </td>
                        <td className="font-mono font-bold text-[#12345A]">
                          {inst.institution_code}
                        </td>
                        <td>
                          <div className="font-semibold text-[#12345A]">{inst.name}</div>
                          {inst.contact_email && (
                            <div className="text-[11px] text-[#5F6B76] flex items-center gap-1 mt-0.5">
                              <Mail size={11} />
                              <span>{inst.contact_email}</span>
                            </div>
                          )}
                        </td>
                        <td>
                          <span className="gov-badge gov-badge-neutral">
                            {inst.category}
                          </span>
                        </td>
                        <td className="text-xs text-[#202B36]">
                          <div className="flex items-center gap-1">
                            <MapPin size={12} className="text-[#5F6B76]" />
                            <span>{inst.district}, {inst.state}</span>
                          </div>
                        </td>
                        <td>
                          <button
                            onClick={() => toggleExpand(inst.id)}
                            className="text-[#174F82] hover:text-[#12345A] font-semibold text-xs flex items-center gap-1"
                          >
                            <Layers size={12} />
                            <span>{inst.programme_count} Active</span>
                          </button>
                        </td>
                        <td>
                          <span className="gov-badge gov-badge-verified">
                            {inst.approval_status}
                          </span>
                        </td>
                        <td className="text-right">
                          <button
                            onClick={() => handleOpenAddProg(inst)}
                            className="gov-btn-secondary text-xs py-1 px-2.5 inline-flex items-center gap-1"
                          >
                            <Plus size={12} />
                            <span>Add Programme</span>
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Programmes Accordion */}
                      {isExpanded && (
                        <tr>
                          <td colSpan={8} className="p-4 bg-[#F4F6F8] border-b border-[#D7DEE5]">
                            <div className="bg-white border border-[#D7DEE5] rounded p-4 shadow-xs">
                              <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#D7DEE5]">
                                <div className="font-bold text-xs uppercase text-[#12345A] flex items-center gap-1.5">
                                  <BookOpen size={14} className="text-[#174F82]" />
                                  <span>Academic Programmes Catalogue — {inst.name}</span>
                                </div>
                                <button
                                  onClick={() => handleOpenAddProg(inst)}
                                  className="gov-btn-primary text-xs py-1 px-2.5 flex items-center gap-1"
                                >
                                  <Plus size={11} />
                                  <span>New Programme</span>
                                </button>
                              </div>

                              {isProgLoading ? (
                                <div className="p-4 text-center text-[#5F6B76] text-xs">
                                  Loading programmes...
                                </div>
                              ) : progs.length === 0 ? (
                                <div className="p-4 text-center text-[#5F6B76] text-xs">
                                  No programmes configured for this institution yet.{' '}
                                  <button
                                    onClick={() => handleOpenAddProg(inst)}
                                    className="text-[#174F82] font-semibold underline ml-1"
                                  >
                                    Add the first programme
                                  </button>
                                </div>
                              ) : (
                                <table className="gov-table w-full text-xs">
                                  <thead>
                                    <tr>
                                      <th>Programme Code</th>
                                      <th>Programme Name</th>
                                      <th>Level</th>
                                      <th>Duration</th>
                                      <th>Approved Intake Capacity</th>
                                      <th>Status</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {progs.map((p) => (
                                      <tr key={p.id}>
                                        <td className="font-mono font-bold text-[#12345A]">
                                          {p.programme_code}
                                        </td>
                                        <td className="font-semibold text-[#202B36]">
                                          {p.programme_name}
                                        </td>
                                        <td>
                                          <span className="gov-badge gov-badge-info">
                                            {p.qualification_level}
                                          </span>
                                        </td>
                                        <td className="text-[#5F6B76]">
                                          {p.duration_years} Years
                                        </td>
                                        <td className="font-mono font-semibold text-[#12345A]">
                                          {p.approved_intake ? (
                                            <span>{p.approved_intake} seats ({p.academic_year || 'Active'})</span>
                                          ) : (
                                            <span className="text-[#8C9BA8]">Standard</span>
                                          )}
                                        </td>
                                        <td>
                                          <span className="gov-badge gov-badge-verified">
                                            {p.status}
                                          </span>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Register Institution */}
      {showInstModal && (
        <div className="fixed inset-0 bg-[#0F172A]/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded border border-[#CBD7E3] max-w-lg w-full shadow-lg overflow-hidden">
            <div className="p-4 border-b border-[#D7DEE5] flex items-center justify-between bg-[#F4F6F8]">
              <div className="flex items-center gap-2">
                <Building2 size={18} className="text-[#12345A]" />
                <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
                  Register New Institution / नया संस्थान दर्ज करें
                </h3>
              </div>
              <button
                onClick={() => setShowInstModal(false)}
                className="text-[#5F6B76] hover:text-[#12345A]"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateInstitution} className="p-5 space-y-4">
              {formError && (
                <div className="bg-red-50 border border-red-200 text-red-900 p-2.5 rounded text-xs flex gap-2 items-center">
                  <AlertCircle size={14} className="shrink-0 text-red-700" />
                  <span>{formError}</span>
                </div>
              )}
              {formSuccess && (
                <div className="bg-[#EAF7EE] border border-[#23834A] text-[#166534] p-2.5 rounded text-xs flex gap-2 items-center">
                  <CheckCircle size={14} className="shrink-0 text-[#23834A]" />
                  <span>{formSuccess}</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Institution Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. AIT"
                    value={newInst.institution_code}
                    onChange={(e) => setNewInst({ ...newInst, institution_code: e.target.value })}
                    className="gov-input font-mono uppercase text-xs w-full"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Institution Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Apex Institute of Technology"
                    value={newInst.name}
                    onChange={(e) => setNewInst({ ...newInst, name: e.target.value })}
                    className="gov-input text-xs w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Category *
                  </label>
                  <select
                    value={newInst.category}
                    onChange={(e) => setNewInst({ ...newInst, category: e.target.value })}
                    className="gov-input text-xs w-full"
                  >
                    <option value="ENGINEERING">ENGINEERING</option>
                    <option value="POLYTECHNIC">POLYTECHNIC</option>
                    <option value="UNIVERSITY">UNIVERSITY</option>
                    <option value="MANAGEMENT">MANAGEMENT</option>
                    <option value="PHARMACY">PHARMACY</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Contact Email
                  </label>
                  <input
                    type="email"
                    placeholder="registrar@apextech.ac.in"
                    value={newInst.contact_email}
                    onChange={(e) => setNewInst({ ...newInst, contact_email: e.target.value })}
                    className="gov-input text-xs w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    State *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Maharashtra"
                    value={newInst.state}
                    onChange={(e) => setNewInst({ ...newInst, state: e.target.value })}
                    className="gov-input text-xs w-full"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    District *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Pune"
                    value={newInst.district}
                    onChange={(e) => setNewInst({ ...newInst, district: e.target.value })}
                    className="gov-input text-xs w-full"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Pincode
                  </label>
                  <input
                    type="text"
                    placeholder="411001"
                    value={newInst.pincode}
                    onChange={(e) => setNewInst({ ...newInst, pincode: e.target.value })}
                    className="gov-input text-xs w-full"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Official Campus Address
                </label>
                <input
                  type="text"
                  placeholder="Campus Road, Pune"
                  value={newInst.address}
                  onChange={(e) => setNewInst({ ...newInst, address: e.target.value })}
                  className="gov-input text-xs w-full"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-[#D7DEE5]">
                <button
                  type="button"
                  onClick={() => setShowInstModal(false)}
                  className="gov-btn-secondary text-xs py-1.5 px-3"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="gov-btn-primary text-xs py-1.5 px-4"
                >
                  {isSubmitting ? 'Registering...' : 'Save Institution'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Academic Programme */}
      {showProgModal && targetInstForProg && (
        <div className="fixed inset-0 bg-[#0F172A]/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded border border-[#CBD7E3] max-w-lg w-full shadow-lg overflow-hidden">
            <div className="p-4 border-b border-[#D7DEE5] flex items-center justify-between bg-[#F4F6F8]">
              <div className="flex items-center gap-2">
                <BookOpen size={18} className="text-[#12345A]" />
                <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
                  Add Academic Programme / नया पाठ्यक्रम जोड़ें
                </h3>
              </div>
              <button
                onClick={() => setShowProgModal(false)}
                className="text-[#5F6B76] hover:text-[#12345A]"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateProgramme} className="p-5 space-y-4">
              <div className="bg-[#EAF2F8] border border-[#CBD7E3] rounded p-2.5 text-xs text-[#12345A]">
                Registering programme under: <strong>{targetInstForProg.name} ({targetInstForProg.institution_code})</strong>
              </div>

              {formError && (
                <div className="bg-red-50 border border-red-200 text-red-900 p-2.5 rounded text-xs flex gap-2 items-center">
                  <AlertCircle size={14} className="shrink-0 text-red-700" />
                  <span>{formError}</span>
                </div>
              )}
              {formSuccess && (
                <div className="bg-[#EAF7EE] border border-[#23834A] text-[#166534] p-2.5 rounded text-xs flex gap-2 items-center">
                  <CheckCircle size={14} className="shrink-0 text-[#23834A]" />
                  <span>{formSuccess}</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Programme Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CSE"
                    value={newProg.programme_code}
                    onChange={(e) => setNewProg({ ...newProg, programme_code: e.target.value })}
                    className="gov-input font-mono uppercase text-xs w-full"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Programme Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. B.Tech Computer Science and Engineering"
                    value={newProg.programme_name}
                    onChange={(e) => setNewProg({ ...newProg, programme_name: e.target.value })}
                    className="gov-input text-xs w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Qualification Level *
                  </label>
                  <select
                    value={newProg.qualification_level}
                    onChange={(e) => setNewProg({ ...newProg, qualification_level: e.target.value })}
                    className="gov-input text-xs w-full"
                  >
                    <option value="UG">UG (Undergraduate)</option>
                    <option value="PG">PG (Postgraduate)</option>
                    <option value="DIPLOMA">DIPLOMA</option>
                    <option value="PHD">PHD (Doctoral)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Duration (Years) *
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={6}
                    required
                    value={newProg.duration_years}
                    onChange={(e) => setNewProg({ ...newProg, duration_years: parseInt(e.target.value) || 4 })}
                    className="gov-input text-xs w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Approved Intake Capacity
                  </label>
                  <input
                    type="number"
                    min={0}
                    placeholder="120"
                    value={newProg.approved_intake}
                    onChange={(e) => setNewProg({ ...newProg, approved_intake: parseInt(e.target.value) || 0 })}
                    className="gov-input font-mono text-xs w-full"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                    Academic Year
                  </label>
                  <select
                    value={newProg.academic_year}
                    onChange={(e) => setNewProg({ ...newProg, academic_year: e.target.value })}
                    className="gov-input text-xs w-full"
                  >
                    <option value="2024-25">2024-25</option>
                    <option value="2025-26">2025-26</option>
                    <option value="2023-24">2023-24</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-[#D7DEE5]">
                <button
                  type="button"
                  onClick={() => setShowProgModal(false)}
                  className="gov-btn-secondary text-xs py-1.5 px-3"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="gov-btn-primary text-xs py-1.5 px-4"
                >
                  {isSubmitting ? 'Adding...' : 'Save Programme'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
