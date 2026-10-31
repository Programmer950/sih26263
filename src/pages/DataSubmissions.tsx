import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Upload,
  CheckCircle,
  XCircle,
  ArrowRight,
  RefreshCw,
  ChevronRight,
  Eye,
  Check,
  AlertCircle,
  Building2,
  BookOpen,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  uploadSubmissionFile,
  generateSubmissionPreview,
  confirmSubmissionIngestion,
  listSubmissions,
  UploadResponse,
  PreviewResponse,
  ConfirmResponse,
  SubmissionSummary,
} from '../services/submissions';
import api, { extractErrorMessage } from '../services/api';

export const DataSubmissions: React.FC = () => {
  const { user } = useAuth();

  // Wizard Steps: 1: Select & Upload, 2: Map Columns, 3: Preview & Validate, 4: Confirmed
  const [step, setStep] = useState<number>(1);

  // Form State
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [programmes, setProgrammes] = useState<any[]>([]);
  const [selectedInstId, setSelectedInstId] = useState<string>('');
  const [selectedProgId, setSelectedProgId] = useState<string>('');
  const [academicYear, setAcademicYear] = useState<string>('2025-26');
  const [submissionType, setSubmissionType] = useState<string>('ANNUAL_ROSTER');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Processing & Responses
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [isPreviewing, setIsPreviewing] = useState<boolean>(false);
  const [previewResult, setPreviewResult] = useState<PreviewResponse | null>(null);
  const [isConfirming, setIsConfirming] = useState<boolean>(false);
  const [confirmResult, setConfirmResult] = useState<ConfirmResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Submissions History
  const [history, setHistory] = useState<SubmissionSummary[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);

  // Standard Target Fields
  const standardFields = [
    { key: 'institution_student_id', label: 'Roll Number / Student ID', required: true },
    { key: 'full_name', label: 'Student Full Name', required: true },
    { key: 'apaar_id', label: 'APAAR ID (12-Digit Reference)', required: false },
    { key: 'date_of_birth', label: 'Date of Birth (YYYY-MM-DD)', required: false },
    { key: 'gender', label: 'Gender (M/F/O)', required: false },
    { key: 'admission_date', label: 'Admission Date', required: false },
    { key: 'admission_category', label: 'Admission Category (REGULAR/TFW/NRI)', required: false },
    { key: 'student_status', label: 'Enrollment Status (ACTIVE/WITHDRAWN)', required: false },
  ];

  // Fetch initial institutions and programmes
  useEffect(() => {
    loadInstitutions();
    loadHistory();
  }, []);

  const loadInstitutions = async () => {
    try {
      const res = await api.get('/institutions');
      const instList = res.data.items || res.data || [];
      setInstitutions(instList);
      if (instList.length > 0) {
        const defaultInst = user?.institution_id
          ? instList.find((i: any) => i.id === user.institution_id) || instList[0]
          : instList[0];
        setSelectedInstId(defaultInst.id);
        loadProgrammes(defaultInst.id);
      } else {
        setSelectedInstId('');
        setProgrammes([]);
        setSelectedProgId('');
      }
    } catch (err: any) {
      console.error('Failed to load institutions:', err);
    }
  };

  const loadProgrammes = async (instId: string) => {
    if (!instId) {
      setProgrammes([]);
      setSelectedProgId('');
      return;
    }
    try {
      const res = await api.get(`/institutions/${instId}/programmes`);
      const progList = res.data.items || res.data || [];
      setProgrammes(progList);
      if (progList.length > 0) {
        setSelectedProgId(progList[0].id);
      } else {
        setSelectedProgId('');
      }
    } catch (err: any) {
      console.error('Failed to load programmes:', err);
      setProgrammes([]);
      setSelectedProgId('');
    }
  };

  const loadHistory = async () => {
    try {
      setIsLoadingHistory(true);
      const res = await listSubmissions({ limit: 10 });
      setHistory(res.items || []);
    } catch (err: any) {
      console.error('Failed to load submission history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a CSV or XLSX roster file to upload.');
      return;
    }
    if (!selectedProgId) {
      setError('Please select an academic programme.');
      return;
    }

    try {
      setIsUploading(true);
      setError(null);
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('programme_id', selectedProgId);
      formData.append('academic_year', academicYear);
      formData.append('submission_type', submissionType);
      if (selectedInstId) {
        formData.append('institution_id', selectedInstId);
      }

      const res = await uploadSubmissionFile(formData);
      setUploadResult(res);

      // Initialize column mappings from suggested mappings
      const initialMap: Record<string, string> = {};
      standardFields.forEach((f) => {
        if (res.suggested_mapping && res.suggested_mapping[f.key]) {
          initialMap[f.key] = res.suggested_mapping[f.key] as string;
        } else if (res.detected_headers.includes(f.key)) {
          initialMap[f.key] = f.key;
        }
      });
      setColumnMapping(initialMap);
      setStep(2);
    } catch (err: any) {
      setError(extractErrorMessage(err, 'File upload failed.'));
    } finally {
      setIsUploading(false);
    }
  };

  const handleGeneratePreview = async () => {
    if (!uploadResult) return;
    try {
      setIsPreviewing(true);
      setError(null);
      const res = await generateSubmissionPreview(uploadResult.submission_id, columnMapping);
      setPreviewResult(res);
      setStep(3);
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Validation preview failed.'));
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleConfirmIngestion = async () => {
    if (!uploadResult || !previewResult) return;
    try {
      setIsConfirming(true);
      setError(null);
      const res = await confirmSubmissionIngestion(uploadResult.submission_id, {
        preview_id: previewResult.preview_id,
        column_mapping: columnMapping,
        completeness_status: 'COMPLETE',
        mark_as_authoritative: true,
      });
      setConfirmResult(res);
      setStep(4);
      loadHistory();
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Ingestion confirmation failed.'));
    } finally {
      setIsConfirming(false);
    }
  };

  const resetWizard = () => {
    setStep(1);
    setSelectedFile(null);
    setUploadResult(null);
    setPreviewResult(null);
    setConfirmResult(null);
    setError(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="gov-badge gov-badge-info">
            Statutory Data Ingestion Portal
          </span>
          <span className="text-[11px] text-[#5F6B76] font-mono">Module 4 — Longitudinal Ingestion</span>
        </div>
        <h1 className="text-xl font-bold text-[#12345A] mt-1.5 uppercase tracking-wide">
          Annual Student Roster Submissions / वार्षिक छात्र पंजीयन
        </h1>
        <p className="text-xs text-[#5F6B76] mt-0.5">
          Deterministic, idempotent upload of institutional student rosters with pre-flight schema validation, header mapping, and immutable SHA-256 provenance archiving.
        </p>
      </div>

      {/* Progress Stepper */}
      <div className="bg-white border border-[#D7DEE5] rounded p-4 flex items-center justify-between shadow-sm overflow-x-auto">
        {[
          { num: 1, label: 'Upload & Context' },
          { num: 2, label: 'Column Mapping' },
          { num: 3, label: 'Preview & Validate' },
          { num: 4, label: 'Confirmed Snapshot' },
        ].map((s, idx) => (
          <React.Fragment key={s.num}>
            <div className="flex items-center gap-3">
              <div
                className={`w-7 h-7 rounded flex items-center justify-center font-bold text-xs font-mono ${
                  step >= s.num ? 'bg-[#12345A] text-white' : 'bg-[#EAF2F8] text-[#5F6B76] border border-[#CBD7E3]'
                }`}
              >
                {step > s.num ? <Check size={14} /> : s.num}
              </div>
              <span
                className={`text-xs uppercase tracking-wider ${
                  step === s.num ? 'font-bold text-[#12345A]' : 'font-medium text-[#5F6B76]'
                }`}
              >
                {s.label}
              </span>
            </div>
            {idx < 3 && <ChevronRight size={16} className="text-[#8C9BA8] mx-2" />}
          </React.Fragment>
        ))}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded text-xs flex items-center gap-2 shadow-xs">
          <XCircle size={16} className="text-red-700 shrink-0" />
          <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
        </div>
      )}

      {/* Step 1: Upload & Context */}
      {step === 1 && (
        <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-5">
          <div className="border-b border-[#D7DEE5] pb-3">
            <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Step 1: Select Academic Context & Upload Roster File
            </h2>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Select your institution and registered academic programme before uploading the student roster CSV.
            </p>
          </div>

          {institutions.length === 0 && (
            <div className="bg-red-50 border border-red-200 rounded p-4 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <AlertCircle size={20} className="text-red-700 shrink-0" />
                <div>
                  <div className="font-bold text-red-950 text-xs uppercase tracking-wide">
                    No Registered Institutions Found
                  </div>
                  <div className="text-xs text-red-800 mt-0.5">
                    Before uploading student CSV rosters, you must register your institution and its programmes in the registry.
                  </div>
                </div>
              </div>
              <Link
                to="/app/institutions"
                className="gov-btn-primary bg-red-700 hover:bg-red-800 text-xs py-1.5 px-3 flex items-center gap-1.5"
              >
                <Building2 size={14} />
                <span>Register Institution</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          )}

          {institutions.length > 0 && programmes.length === 0 && (
            <div className="bg-[#FFF8E7] border border-[#FDE68A] rounded p-4 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <AlertCircle size={20} className="text-[#8F6B00] shrink-0" />
                <div>
                  <div className="font-bold text-[#8F6B00] text-xs uppercase tracking-wide">
                    No Academic Programmes Registered for Selected Institution
                  </div>
                  <div className="text-xs text-[#8F6B00] mt-0.5">
                    Please add an approved programme (e.g. CSE, IT) under this institution to enable student roster uploads.
                  </div>
                </div>
              </div>
              <Link
                to="/app/institutions"
                className="gov-btn-primary bg-[#8F6B00] hover:bg-[#735600] text-xs py-1.5 px-3 flex items-center gap-1.5"
              >
                <BookOpen size={14} />
                <span>Add Programme</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          )}

          <form onSubmit={handleUpload} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Institution
                </label>
                <select
                  value={selectedInstId}
                  onChange={(e) => {
                    setSelectedInstId(e.target.value);
                    loadProgrammes(e.target.value);
                  }}
                  disabled={institutions.length === 0}
                  className="gov-input text-xs w-full"
                >
                  {institutions.length === 0 ? (
                    <option value="">No institutions registered</option>
                  ) : (
                    institutions.map((inst) => (
                      <option key={inst.id} value={inst.id}>
                        {inst.name || inst.institution_name} ({inst.institution_code})
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Academic Programme
                </label>
                <select
                  value={selectedProgId}
                  onChange={(e) => setSelectedProgId(e.target.value)}
                  disabled={programmes.length === 0}
                  className="gov-input text-xs w-full"
                >
                  {programmes.length === 0 ? (
                    <option value="">No programmes available</option>
                  ) : (
                    programmes.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.programme_name} ({p.programme_code})
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Academic Year
                </label>
                <select
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  className="gov-input text-xs w-full"
                >
                  <option value="2025-26">2025-26 (Candidate Cohort)</option>
                  <option value="2024-25">2024-25 (Baseline Cohort)</option>
                  <option value="2023-24">2023-24 (Historical Census)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-[#12345A] mb-1">
                  Submission Category
                </label>
                <select
                  value={submissionType}
                  onChange={(e) => setSubmissionType(e.target.value)}
                  className="gov-input text-xs w-full"
                >
                  <option value="ANNUAL_ROSTER">Annual Student Roster (Authoritative)</option>
                  <option value="LATERAL_ENTRY_LIST">Lateral Entry Inflow List</option>
                  <option value="MID_YEAR_CORRECTION">Mid-Year Correction Roster</option>
                </select>
              </div>
            </div>

            {/* Drag & Drop File Upload Box */}
            <div
              className="border-2 border-dashed border-[#CBD7E3] hover:border-[#174F82] rounded p-8 text-center bg-[#F4F6F8] cursor-pointer transition"
              onClick={() => document.getElementById('roster-file-input')?.click()}
            >
              <Upload size={32} className="text-[#174F82] mx-auto mb-2" />
              <p className="text-xs font-bold text-[#12345A] mb-1">
                {selectedFile ? selectedFile.name : 'Select or Drag & Drop Student Roster File (CSV / XLSX)'}
              </p>
              <p className="text-[11px] text-[#5F6B76]">
                Maximum file size: 10MB. Files are cryptographically fingerprinted (SHA-256) upon upload.
              </p>
              <input
                id="roster-file-input"
                type="file"
                accept=".csv, .xlsx, text/csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={isUploading || !selectedFile}
                className="gov-btn-primary text-xs py-2 px-5 flex items-center gap-2"
              >
                {isUploading ? <RefreshCw size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                {isUploading ? 'Uploading & Inspecting Headers...' : 'Upload & Proceed to Column Mapping'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Step 2: Column Mapping */}
      {step === 2 && uploadResult && (
        <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-[#D7DEE5] gap-2">
            <div>
              <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
                Step 2: Header Inspection & Column Mapping
              </h2>
              <p className="text-xs text-[#5F6B76] mt-0.5">
                Detected {uploadResult.detected_headers.length} headers in <strong>{uploadResult.original_filename}</strong>. Map each required field to the detected source column.
              </p>
            </div>
            <div className="bg-[#EAF2F8] border border-[#CBD7E3] px-2.5 py-1 rounded text-[11px] font-mono text-[#12345A]">
              SHA-256: {uploadResult.file_fingerprint.slice(0, 16)}...
            </div>
          </div>

          <div className="gov-table-container">
            <table className="gov-table w-full">
              <thead>
                <tr>
                  <th>Standard Institutional Field</th>
                  <th>Requirement</th>
                  <th>Matched Source Column</th>
                  <th>Sample Value (Row 1)</th>
                </tr>
              </thead>
              <tbody>
                {standardFields.map((field) => {
                  const sampleRow = uploadResult.sample_rows?.[0]?.raw_payload || {};
                  const mappedCol = columnMapping[field.key] || '';
                  return (
                    <tr key={field.key}>
                      <td className="font-semibold text-[#12345A]">{field.label}</td>
                      <td>
                        {field.required ? (
                          <span className="gov-badge gov-badge-danger">Mandatory</span>
                        ) : (
                          <span className="gov-badge gov-badge-neutral">Optional</span>
                        )}
                      </td>
                      <td>
                        <select
                          value={mappedCol}
                          onChange={(e) => setColumnMapping({ ...columnMapping, [field.key]: e.target.value })}
                          className="gov-input text-xs w-64"
                        >
                          <option value="">-- Do Not Map --</option>
                          {uploadResult.detected_headers.map((h) => (
                            <option key={h} value={h}>
                              {h}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="font-mono text-xs text-[#5F6B76]">
                        {mappedCol ? String(sampleRow[mappedCol] ?? '-') : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={() => setStep(1)}
              className="gov-btn-secondary text-xs py-2 px-4"
            >
              Back
            </button>
            <button
              onClick={handleGeneratePreview}
              disabled={isPreviewing}
              className="gov-btn-primary text-xs py-2 px-5 flex items-center gap-2"
            >
              {isPreviewing ? <RefreshCw size={14} className="animate-spin" /> : <Eye size={14} />}
              {isPreviewing ? 'Validating Full Roster...' : 'Generate Validation Preview'}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview & Validate */}
      {step === 3 && previewResult && (
        <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
          <div className="border-b border-[#D7DEE5] pb-3">
            <h2 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Step 3: Full Roster Pre-Flight Validation Summary
            </h2>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Review schema validation findings before committing records to the authoritative institutional ledger.
            </p>
          </div>

          {/* Validation Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-3 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#12345A]">
              <div className="text-[10px] font-bold text-[#5F6B76] uppercase">Total Rows</div>
              <div className="text-2xl font-bold text-[#12345A] font-mono mt-0.5">
                {previewResult.total_rows_count}
              </div>
            </div>
            <div className="p-3 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#23834A]">
              <div className="text-[10px] font-bold text-[#23834A] uppercase">Valid Records</div>
              <div className="text-2xl font-bold text-[#23834A] font-mono mt-0.5">
                {previewResult.valid_rows_count}
              </div>
            </div>
            <div className="p-3 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#E58A24]">
              <div className="text-[10px] font-bold text-[#E58A24] uppercase">Warning Rows</div>
              <div className="text-2xl font-bold text-[#E58A24] font-mono mt-0.5">
                {previewResult.warning_rows_count}
              </div>
            </div>
            <div className="p-3 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#C0392B]">
              <div className="text-[10px] font-bold text-[#C0392B] uppercase">Fatal Errors</div>
              <div className="text-2xl font-bold text-[#C0392B] font-mono mt-0.5">
                {previewResult.error_rows_count}
              </div>
            </div>
            <div className="p-3 rounded border border-[#D7DEE5] bg-white border-l-4 border-l-[#8F6B00]">
              <div className="text-[10px] font-bold text-[#8F6B00] uppercase">Duplicates</div>
              <div className="text-2xl font-bold text-[#8F6B00] font-mono mt-0.5">
                {previewResult.duplicate_rows_count}
              </div>
            </div>
          </div>

          <div className="bg-[#EAF2F8] border border-[#CBD7E3] rounded p-3 text-xs text-[#12345A] flex items-center gap-2">
            <span className="font-bold">Statutory Ingestion Protocol:</span>
            <span>
              Confirming this submission creates immutable annual observations and generates an authoritative Roster Snapshot hashed into the tamper-evident audit ledger.
            </span>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={() => setStep(2)}
              className="gov-btn-secondary text-xs py-2 px-4"
            >
              Back to Mapping
            </button>
            <button
              onClick={handleConfirmIngestion}
              disabled={isConfirming || previewResult.error_rows_count > 0}
              className="gov-btn-primary text-xs py-2 px-5 flex items-center gap-2"
            >
              {isConfirming ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle size={14} />}
              {isConfirming ? 'Committing Snapshot...' : 'Confirm Atomic Ingestion'}
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Confirmed Snapshot */}
      {step === 4 && confirmResult && (
        <div className="bg-white border border-[#23834A] rounded p-8 shadow-sm text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-[#EAF7EE] text-[#23834A] border border-[#23834A] flex items-center justify-center mx-auto">
            <CheckCircle size={24} />
          </div>
          <div>
            <h2 className="text-base font-bold text-[#12345A] uppercase tracking-wide">
              Student Roster Committed Successfully / पंजीयन सुरक्षित
            </h2>
            <p className="text-xs text-[#5F6B76] max-w-lg mx-auto mt-1">
              Ingested {confirmResult.total_records_processed} student records. An authoritative snapshot has been sealed and chained to the tamper-evident audit ledger.
            </p>
          </div>

          <div className="bg-[#F4F6F8] border border-[#D7DEE5] rounded p-4 max-w-md mx-auto text-left text-xs font-mono space-y-1">
            <div><span className="text-[#5F6B76]">Submission ID:</span> <span className="font-bold text-[#12345A]">{confirmResult.submission_id}</span></div>
            {confirmResult.snapshot_id && <div><span className="text-[#5F6B76]">Snapshot ID:</span> <span className="text-[#174F82]">{confirmResult.snapshot_id}</span></div>}
            <div><span className="text-[#5F6B76]">Status:</span> <span className="gov-badge gov-badge-verified">{confirmResult.submission_status}</span></div>
            <div><span className="text-[#5F6B76]">Committed At:</span> <span className="text-[#202B36]">{new Date(confirmResult.committed_at).toLocaleString()}</span></div>
          </div>

          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={resetWizard}
              className="gov-btn-secondary text-xs py-2 px-4"
            >
              Upload Another Roster
            </button>
            <a
              href="/app/cohort-explorer"
              className="gov-btn-primary text-xs py-2 px-5 inline-flex items-center gap-1.5"
            >
              Inspect in Cohort Explorer →
            </a>
          </div>
        </div>
      )}

      {/* Historical Submissions Table */}
      <div className="bg-white border border-[#D7DEE5] rounded p-5 shadow-sm space-y-4">
        <div className="flex justify-between items-center pb-3 border-b border-[#D7DEE5]">
          <div>
            <h3 className="text-sm font-bold text-[#12345A] uppercase tracking-wide">
              Recent Roster Submission History / हालिया प्रस्तुतियां
            </h3>
            <p className="text-xs text-[#5F6B76] mt-0.5">
              Immutable register of uploaded rosters, cryptographic SHA-256 digests, and validation transitions.
            </p>
          </div>
          <button
            onClick={loadHistory}
            disabled={isLoadingHistory}
            className="gov-btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
          >
            <RefreshCw size={13} className={isLoadingHistory ? 'animate-spin' : ''} />
            Refresh Log
          </button>
        </div>

        <div className="gov-table-container">
          <table className="gov-table w-full">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Academic Year</th>
                <th>Status</th>
                <th>Records</th>
                <th>SHA-256 Digest</th>
                <th>Committed At</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[#5F6B76]">
                    No submission history recorded.
                  </td>
                </tr>
              ) : (
                history.map((sub) => (
                  <tr key={sub.id}>
                    <td className="font-semibold text-[#12345A]">{sub.original_filename}</td>
                    <td className="font-mono text-xs">{sub.academic_year}</td>
                    <td>
                      <span
                        className={`gov-badge ${
                          sub.submission_status === 'COMMITTED'
                            ? 'gov-badge-verified'
                            : sub.submission_status === 'PREVIEW_READY'
                            ? 'gov-badge-info'
                            : 'gov-badge-neutral'
                        }`}
                      >
                        {sub.submission_status}
                      </span>
                    </td>
                    <td className="font-mono text-xs font-bold text-[#12345A]">{sub.total_rows_count ?? '-'}</td>
                    <td className="font-mono text-[11px] text-[#5F6B76]">
                      {sub.file_fingerprint.slice(0, 16)}...
                    </td>
                    <td className="text-xs text-[#5F6B76]">
                      {sub.committed_at ? new Date(sub.committed_at).toLocaleDateString() : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
