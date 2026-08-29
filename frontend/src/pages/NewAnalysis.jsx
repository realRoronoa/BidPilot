import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  UploadCloud, FileText, CheckCircle2, Building2, Plus, Loader2, X, ArrowRight, ArrowLeft, ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtBytes } from "@/lib/format";
import { StatusBadge } from "@/components/common";
import { toast } from "sonner";

const STEP_LABELS = ["Tender", "Company", "Evidence", "Review", "Analyze"];

export default function NewAnalysis() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [tender, setTender] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [companies, setCompanies] = useState([]);
  const [companyId, setCompanyId] = useState(null);
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState({});
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef();

  useEffect(() => {
    api.get("/companies").then((c) => { setCompanies(c); if (c[0]) setCompanyId(c[0].id); });
    api.get("/documents?doc_type=company").then((d) => {
      setDocs(d); const sel = {}; d.forEach((x) => (sel[x.id] = true)); setSelected(sel);
    });
  }, []);

  const uploadTender = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) { toast.error("Only PDF files are supported."); return; }
    setUploading(true); setProgress(0);
    const fd = new FormData();
    fd.append("file", file); fd.append("doc_type", "tender"); fd.append("category", "Tender");
    try {
      const res = await api.upload("/documents", fd, (e) => setProgress(Math.round((e.loaded / e.total) * 100)));
      setTender(res);
      if (res.notice) toast.warning(res.notice);
      else toast.success("Tender uploaded and parsed");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Upload failed");
    }
    setUploading(false);
  };

  const uploadEvidence = async (file, category = "Other") => {
    const fd = new FormData();
    fd.append("file", file); fd.append("doc_type", "company"); fd.append("category", category);
    if (companyId) fd.append("company_id", companyId);
    try {
      const res = await api.upload("/documents", fd);
      setDocs((d) => [res, ...d]); setSelected((s) => ({ ...s, [res.id]: true }));
      toast.success("Evidence added");
    } catch (e) { toast.error(e.response?.data?.detail || "Upload failed"); }
  };

  const createCompany = async (form) => {
    setCreating(true);
    try {
      const c = await api.post("/company", form);
      setCompanies((cs) => [...cs, c]); setCompanyId(c.id);
      toast.success("Company created");
    } catch { toast.error("Failed to create company"); }
    setCreating(false);
  };

  const runAnalysis = async () => {
    setSubmitting(true);
    try {
      const evidenceIds = Object.keys(selected).filter((k) => selected[k]);
      const res = await api.post("/analyses", {
        tender_name: tender.filename.replace(/\.pdf$/i, "").replace(/[-_]/g, " "),
        tender_document_id: tender.id, company_id: companyId, evidence_document_ids: evidenceIds,
      });
      navigate(`/analyses/${res.id}`);
    } catch (e) { toast.error(e.response?.data?.detail || "Failed to start analysis"); setSubmitting(false); }
  };

  const company = companies.find((c) => c.id === companyId);
  const canNext = [!!tender, !!companyId, true, true][step];

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 md:px-8">
      <h1 className="font-serif text-3xl font-bold text-ink">New Analysis</h1>
      <p className="mt-1 text-sm text-ink-muted">Compare a tender against your company evidence.</p>

      {/* Stepper */}
      <div className="mt-6 flex items-center">
        {STEP_LABELS.map((l, i) => (
          <React.Fragment key={l}>
            <div className="flex items-center gap-2">
              <span className={`flex h-8 w-8 items-center justify-center rounded-full border-2 font-mono text-xs font-semibold ${i < step ? "border-pass-text bg-pass-text text-white" : i === step ? "border-navy bg-navy text-white" : "border-line bg-panel text-ink-faint"}`}>
                {i < step ? <CheckCircle2 className="h-4 w-4" /> : String(i + 1).padStart(2, "0")}
              </span>
              <span className={`hidden text-sm font-medium sm:block ${i === step ? "text-ink" : "text-ink-faint"}`}>{l}</span>
            </div>
            {i < STEP_LABELS.length - 1 && <div className={`mx-2 h-px flex-1 ${i < step ? "bg-pass-text" : "bg-line"}`} />}
          </React.Fragment>
        ))}
      </div>

      <div className="mt-6 rounded-md border border-line bg-panel p-6 shadow-sm">
        {/* STEP 1: TENDER */}
        {step === 0 && (
          <div>
            <h2 className="font-serif text-xl font-semibold">Upload the tender</h2>
            <p className="mt-1 text-sm text-ink-muted">PDF tender / RFP / bid document. Max 40 MB.</p>
            {!tender ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => { e.preventDefault(); uploadTender(e.dataTransfer.files[0]); }}
                data-testid="tender-dropzone"
                className="mt-5 flex flex-col items-center justify-center rounded-md border-2 border-dashed border-line bg-paper/60 px-6 py-14 text-center">
                {uploading ? (
                  <>
                    <Loader2 className="h-8 w-8 animate-spin text-navy" />
                    <p className="mt-3 text-sm font-medium">Uploading & parsing… {progress}%</p>
                    <div className="mt-2 h-1.5 w-56 overflow-hidden rounded-full bg-divider"><div className="h-full bg-navy" style={{ width: `${progress}%` }} /></div>
                  </>
                ) : (
                  <>
                    <UploadCloud className="h-9 w-9 text-navy" strokeWidth={1.5} />
                    <p className="mt-3 text-sm font-medium">Drag & drop the tender PDF here</p>
                    <p className="text-xs text-ink-muted">or</p>
                    <button data-testid="browse-tender-btn" onClick={() => fileRef.current?.click()} className="mt-2 rounded-md border border-navy px-4 py-2 text-sm font-semibold text-navy hover:bg-navy hover:text-white">Browse files</button>
                    <input ref={fileRef} type="file" accept="application/pdf" hidden onChange={(e) => uploadTender(e.target.files[0])} />
                  </>
                )}
              </div>
            ) : (
              <div data-testid="tender-preview" className="mt-5 flex items-center gap-4 rounded-md border border-line bg-paper/60 p-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-md bg-navy/10"><FileText className="h-6 w-6 text-navy" /></div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{tender.filename}</div>
                  <div className="font-mono text-xs text-ink-muted">{fmtBytes(tender.size)} · {tender.page_count} pages · <StatusBadgeInline status={tender.status} /></div>
                </div>
                <button data-testid="remove-tender-btn" onClick={() => setTender(null)} className="rounded-md p-2 text-ink-faint hover:bg-secondary hover:text-fail-text"><X className="h-4 w-4" /></button>
              </div>
            )}
          </div>
        )}

        {/* STEP 2: COMPANY */}
        {step === 1 && (
          <CompanyStep companies={companies} companyId={companyId} setCompanyId={setCompanyId} createCompany={createCompany} creating={creating} />
        )}

        {/* STEP 3: EVIDENCE */}
        {step === 2 && (
          <EvidenceStep docs={docs} selected={selected} setSelected={setSelected} uploadEvidence={uploadEvidence} />
        )}

        {/* STEP 4: REVIEW */}
        {step === 3 && (
          <div>
            <h2 className="font-serif text-xl font-semibold">Review before analysis</h2>
            <div className="mt-4 space-y-3">
              <ReviewRow label="Tender" value={tender?.filename} sub={`${tender?.page_count} pages · ${fmtBytes(tender?.size)}`} />
              <ReviewRow label="Company" value={company?.legal_name} sub={company?.specialization} />
              <ReviewRow label="Evidence selected" value={`${Object.values(selected).filter(Boolean).length} documents`} />
            </div>
            <div className="mt-5 rounded-md border border-line bg-paper/60 p-4">
              <div className="text-sm font-semibold text-ink">What BidPilot will analyze</div>
              <ul className="mt-2 grid grid-cols-2 gap-1.5 text-sm text-ink-muted">
                {["Eligibility", "Compliance", "Technical qualification", "Company evidence", "Commercial risks", "Evidence traceability", "Decision readiness"].map((x) => (
                  <li key={x} className="flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5 text-pass-text" /> {x}</li>
                ))}
              </ul>
            </div>
            <p className="mt-4 flex items-center gap-2 font-mono text-xs text-ink-muted"><ShieldCheck className="h-3.5 w-3.5" /> BidPilot is decision support and does not replace professional judgment.</p>
          </div>
        )}

        {/* STEP 5: ANALYZE */}
        {step === 4 && (
          <div className="py-6 text-center">
            <h2 className="font-serif text-xl font-semibold">Ready to analyze</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-ink-muted">BidPilot will read the tender, extract requirements, match them against your evidence, surface risks, and produce a recommendation. This runs in the background and typically takes under two minutes.</p>
            <button data-testid="run-analysis-btn" onClick={runAnalysis} disabled={submitting}
              className="mx-auto mt-6 inline-flex items-center gap-2 rounded-md bg-stamp px-6 py-3 text-base font-semibold text-white hover:bg-stamp-dark disabled:opacity-60">
              {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <ArrowRight className="h-5 w-5" />} Analyze Tender
            </button>
          </div>
        )}
      </div>

      {/* Nav */}
      {step < 4 && (
        <div className="mt-5 flex items-center justify-between">
          <button data-testid="wizard-back" disabled={step === 0} onClick={() => setStep((s) => s - 1)} className="inline-flex items-center gap-1.5 rounded-md border border-line px-4 py-2 text-sm font-medium disabled:opacity-40 hover:bg-secondary">
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <button data-testid="wizard-next" disabled={!canNext} onClick={() => setStep((s) => s + 1)} className="inline-flex items-center gap-1.5 rounded-md bg-navy px-5 py-2 text-sm font-semibold text-white disabled:opacity-40 hover:bg-navy-light">
            Continue <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}

function StatusBadgeInline({ status }) {
  const map = { Processed: "text-pass-text", "Needs Review": "text-review-text", Failed: "text-fail-text" };
  return <span className={`font-semibold ${map[status] || "text-ink-muted"}`}>{status}</span>;
}

function ReviewRow({ label, value, sub }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-divider bg-paper/40 px-4 py-3">
      <span className="text-xs font-medium uppercase tracking-wide text-ink-faint">{label}</span>
      <div className="text-right"><div className="font-medium text-ink">{value || "—"}</div>{sub && <div className="text-xs text-ink-muted">{sub}</div>}</div>
    </div>
  );
}

function CompanyStep({ companies, companyId, setCompanyId, createCompany, creating }) {
  const [showForm, setShowForm] = useState(companies.length === 0);
  const [form, setForm] = useState({ legal_name: "", registration: "", location: "", years_experience: 0, turnover: "", specialization: "" });
  return (
    <div>
      <h2 className="font-serif text-xl font-semibold">Select or create a company</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {companies.map((c) => (
          <button key={c.id} data-testid={`company-card-${c.id}`} onClick={() => { setCompanyId(c.id); setShowForm(false); }}
            className={`rounded-md border p-4 text-left transition-colors ${companyId === c.id && !showForm ? "border-navy ring-2 ring-navy/20" : "border-line hover:bg-secondary"}`}>
            <div className="flex items-center gap-2"><Building2 className="h-4 w-4 text-navy" /><span className="font-medium">{c.legal_name}</span></div>
            <div className="mt-1 text-xs text-ink-muted">{c.location || "—"} · {c.years_experience} yrs · {c.turnover || "—"}</div>
            <div className="mt-1 text-xs text-ink-muted">{c.specialization}</div>
          </button>
        ))}
        <button data-testid="create-company-toggle" onClick={() => { setShowForm(true); setCompanyId(null); }}
          className={`flex items-center justify-center gap-2 rounded-md border-2 border-dashed p-4 text-sm font-medium ${showForm ? "border-navy text-navy" : "border-line text-ink-muted hover:bg-secondary"}`}>
          <Plus className="h-4 w-4" /> Create company
        </button>
      </div>

      {showForm && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {[["legal_name", "Legal name"], ["registration", "Registration no."], ["location", "Location"], ["turnover", "Turnover"], ["specialization", "Specialization"]].map(([k, label]) => (
            <label key={k} className="block"><span className="mb-1 block text-xs font-medium text-ink-muted">{label}</span>
              <input data-testid={`new-company-${k}`} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} className="w-full rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-navy" /></label>
          ))}
          <label className="block"><span className="mb-1 block text-xs font-medium text-ink-muted">Years of experience</span>
            <input type="number" value={form.years_experience} onChange={(e) => setForm({ ...form, years_experience: Number(e.target.value) })} className="w-full rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-navy" /></label>
          <div className="sm:col-span-2">
            <button data-testid="save-new-company" disabled={!form.legal_name || creating} onClick={() => createCompany(form)} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 hover:bg-navy-light">
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Save company
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function EvidenceStep({ docs, selected, setSelected, uploadEvidence }) {
  const ref = useRef();
  const grouped = docs.reduce((acc, d) => { (acc[d.category] = acc[d.category] || []).push(d); return acc; }, {});
  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-xl font-semibold">Company evidence</h2>
        <button data-testid="add-evidence-btn" onClick={() => ref.current?.click()} className="inline-flex items-center gap-1.5 rounded-md border border-navy px-3 py-1.5 text-sm font-semibold text-navy hover:bg-navy hover:text-white">
          <Plus className="h-4 w-4" /> Add evidence
        </button>
        <input ref={ref} type="file" accept="application/pdf" hidden onChange={(e) => e.target.files[0] && uploadEvidence(e.target.files[0])} />
      </div>
      <p className="mt-1 text-sm text-ink-muted">Select the documents BidPilot should use as evidence.</p>
      {docs.length === 0 ? (
        <p className="mt-5 rounded-md border border-dashed border-line p-6 text-center text-sm text-ink-muted">No company documents yet. Upload evidence to continue.</p>
      ) : (
        <div className="mt-4 space-y-4">
          {Object.entries(grouped).map(([cat, items]) => (
            <div key={cat}>
              <div className="mb-1.5 font-mono text-[11px] uppercase tracking-wide text-ink-faint">{cat}</div>
              <div className="space-y-1.5">
                {items.map((d) => (
                  <label key={d.id} data-testid={`evidence-${d.id}`} className="flex cursor-pointer items-center gap-3 rounded-md border border-line px-3 py-2 hover:bg-secondary/50">
                    <input type="checkbox" checked={!!selected[d.id]} onChange={(e) => setSelected((s) => ({ ...s, [d.id]: e.target.checked }))} className="h-4 w-4 accent-navy" />
                    <FileText className="h-4 w-4 text-navy" />
                    <span className="flex-1 truncate text-sm">{d.filename}</span>
                    {d.expiry && <span className="font-mono text-xs text-ink-muted">exp {d.expiry}</span>}
                    <span className="font-mono text-xs text-ink-muted">{d.verification_state}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
