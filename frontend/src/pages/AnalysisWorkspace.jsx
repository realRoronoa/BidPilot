import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  Loader2, CheckCircle2, XCircle, AlertTriangle, RefreshCw, ArrowRight, Eye,
  CalendarClock, FileWarning, ShieldAlert, ListTodo, Download, Layers,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate, decisionClass } from "@/lib/format";
import { PageLoader, StatusBadge, SeverityBadge, DecisionStamp, ScoreBar, ReadinessRing, Confidence, SourceTag, EmptyState } from "@/components/common";
import { toast } from "sonner";

const TABS = ["overview", "requirements", "eligibility", "compliance", "technical", "risks", "evidence", "decision", "action-plan"];
const TAB_LABELS = { overview: "Overview", requirements: "Requirements", eligibility: "Eligibility", compliance: "Compliance", technical: "Technical", risks: "Risks", evidence: "Evidence", decision: "Decision", "action-plan": "Action Plan" };

export default function AnalysisWorkspace() {
  const { id, tab } = useParams();
  const navigate = useNavigate();
  const active = tab && TABS.includes(tab) ? tab : "overview";
  const [analysis, setAnalysis] = useState(null);
  const [status, setStatus] = useState(null);

  const loadAnalysis = useCallback(() => api.get(`/analyses/${id}`).then(setAnalysis).catch(() => setAnalysis(false)), [id]);
  useEffect(() => { loadAnalysis(); }, [loadAnalysis]);

  // Poll while processing
  useEffect(() => {
    if (!analysis || ["completed"].includes(analysis.status)) return;
    if (analysis.status === "failed") return;
    const iv = setInterval(async () => {
      const st = await api.get(`/analyses/${id}/status`);
      setStatus(st);
      if (st.status === "completed" || st.status === "failed") { clearInterval(iv); loadAnalysis(); }
    }, 2000);
    return () => clearInterval(iv);
  }, [analysis, id, loadAnalysis]);

  if (analysis === null) return <PageLoader label="Loading analysis" />;
  if (analysis === false) return <div className="p-8"><EmptyState title="Analysis not found" description="It may have been deleted." /></div>;

  if (analysis.status !== "completed") {
    return <Processing analysis={analysis} status={status} id={id} onRetry={loadAnalysis} />;
  }

  const d = analysis.decision || {};
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/analyses" className="font-mono text-xs text-navy hover:underline">← All analyses</Link>
          <h1 className="mt-1 font-serif text-2xl font-bold text-ink md:text-3xl">{analysis.tender_name}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-ink-muted">
            <span>{analysis.company_name}</span>
            <span className="font-mono text-xs">·</span>
            <span className="font-mono text-xs">{fmtDate(analysis.created_at)}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center rounded-sm border px-3 py-1 text-sm font-semibold ${decisionClass(d.outcome)}`}>{d.outcome}</span>
          <span className="font-mono text-sm font-semibold">{d.readiness_score}%</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-5 flex gap-1 overflow-x-auto border-b border-line scrollbar-thin">
        {TABS.map((t) => (
          <button key={t} data-testid={`tab-${t}`} onClick={() => navigate(`/analyses/${id}/${t}`)}
            className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${active === t ? "border-navy text-navy" : "border-transparent text-ink-muted hover:text-ink"}`}>
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {active === "overview" && <Overview analysis={analysis} id={id} navigate={navigate} />}
        {active === "requirements" && <Requirements id={id} />}
        {active === "eligibility" && <Eligibility id={id} />}
        {active === "compliance" && <Compliance id={id} />}
        {active === "technical" && <Technical id={id} />}
        {active === "risks" && <Risks id={id} />}
        {active === "evidence" && <Evidence id={id} />}
        {active === "decision" && <Decision analysis={analysis} id={id} navigate={navigate} />}
        {active === "action-plan" && <ActionPlan id={id} />}
      </div>
    </div>
  );
}

/* ---------------- PROCESSING ---------------- */
function Processing({ analysis, status, id, onRetry }) {
  const stages = status?.stages || [
    "Reading tender documents", "Extracting requirements", "Identifying eligibility criteria",
    "Matching company qualifications", "Checking compliance requirements", "Analyzing technical requirements",
    "Analyzing commercial/project risks", "Verifying evidence", "Preparing recommendation"];
  const current = status?.stage_index ?? analysis.stage_index ?? 0;
  const failed = (status?.status || analysis.status) === "failed";
  const error = status?.error || analysis.error;

  const retry = async () => { try { await api.post(`/analyses/${id}/run`, {}); toast.success("Re-running analysis"); onRetry(); } catch { toast.error("Retry failed"); } };

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Link to="/analyses" className="font-mono text-xs text-navy hover:underline">← All analyses</Link>
      <h1 className="mt-2 font-serif text-2xl font-bold">{analysis.tender_name}</h1>
      <p className="text-sm text-ink-muted">{analysis.company_name}</p>

      <div className="mt-6 rounded-md border border-line bg-panel p-6 shadow-sm">
        {failed ? (
          <div data-testid="analysis-failed" className="text-center">
            <XCircle className="mx-auto h-10 w-10 text-fail-text" />
            <h2 className="mt-3 font-serif text-xl font-semibold">Analysis failed</h2>
            <p className="mx-auto mt-2 max-w-md rounded-md border border-fail-border bg-fail-bg px-3 py-2 text-sm text-fail-text">{error || "An unexpected error occurred."}</p>
            <button data-testid="retry-btn" onClick={retry} className="mx-auto mt-5 inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light">
              <RefreshCw className="h-4 w-4" /> Retry analysis
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3">
              <Loader2 className="h-6 w-6 animate-spin text-stamp" />
              <div>
                <h2 className="font-serif text-lg font-semibold">Analyzing tender…</h2>
                <p className="font-mono text-xs text-ink-muted">This runs in the background — you can leave and come back.</p>
              </div>
            </div>
            <div className="mt-5 space-y-2">
              {stages.map((s, i) => (
                <div key={s} data-testid={`stage-${i}`} className="flex items-center gap-3">
                  <span className={`flex h-6 w-6 items-center justify-center rounded-full font-mono text-[10px] ${i < current ? "bg-pass-text text-white" : i === current ? "bg-stamp text-white" : "bg-secondary text-ink-faint"}`}>
                    {i < current ? <CheckCircle2 className="h-3.5 w-3.5" /> : i === current ? <Loader2 className="h-3 w-3 animate-spin" /> : String(i + 1).padStart(2, "0")}
                  </span>
                  <span className={`text-sm ${i <= current ? "text-ink" : "text-ink-faint"}`}>{s}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* ---------------- OVERVIEW ---------------- */
function Overview({ analysis, id, navigate }) {
  const d = analysis.decision || {};
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-6">
        <div className="rounded-md border border-line bg-panel p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              <ReadinessRing value={d.readiness_score} />
              <div>
                <div className="font-mono text-[11px] uppercase tracking-widest text-ink-faint">BidPilot recommendation</div>
                <div className="mt-2"><DecisionStamp outcome={d.outcome} size="md" /></div>
              </div>
            </div>
            <div className="grid w-full max-w-xs grid-cols-1 gap-3 sm:grid-cols-2">
              <ScoreBar label="Eligibility" value={d.eligibility} testid="score-eligibility" />
              <ScoreBar label="Compliance" value={d.compliance} testid="score-compliance" />
              <ScoreBar label="Technical" value={d.technical} testid="score-technical" />
              <ScoreBar label="Risk" value={d.risk} testid="score-risk" />
            </div>
          </div>
          <div className="mt-5 grid grid-cols-3 gap-3">
            <Tally icon={CheckCircle2} label="Satisfied" value={d.satisfied_items} cls="text-pass-text" />
            <Tally icon={XCircle} label="Blockers" value={d.blockers} cls="text-fail-text" />
            <Tally icon={AlertTriangle} label="Needs review" value={d.review_items} cls="text-review-text" />
          </div>
        </div>

        <div className="rounded-md border border-line bg-panel p-5 shadow-sm">
          <h3 className="font-serif text-base font-semibold">Recommendation</h3>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">{d.recommendation}</p>
          <div className="mt-4 flex gap-3">
            <button data-testid="view-decision-btn" onClick={() => navigate(`/analyses/${id}/decision`)} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light">View Decision <ArrowRight className="h-4 w-4" /></button>
            <button onClick={() => navigate(`/analyses/${id}/action-plan`)} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold hover:bg-secondary">View Action Plan</button>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <PortfolioImpact analysisId={id} navigate={navigate} />
        <SidePanel icon={CalendarClock} title="Important deadlines">
          {(analysis.deadlines || []).length === 0 ? <p className="text-sm text-ink-muted">None extracted.</p> :
            analysis.deadlines.map((dl, i) => (
              <div key={`${dl.label}-${dl.date}-${i}`} className="flex items-center justify-between py-1.5 text-sm">
                <span>{dl.label}</span><span className="font-mono text-xs text-ink-muted">{fmtDate(dl.date)}</span>
              </div>
            ))}
        </SidePanel>
      </div>
    </div>
  );
}

function Tally({ icon: Icon, label, value, cls }) {
  return (
    <div className="rounded-md border border-divider bg-paper/40 p-3 text-center">
      <Icon className={`mx-auto h-5 w-5 ${cls}`} />
      <div className="mt-1 font-serif text-2xl font-bold">{value ?? 0}</div>
      <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{label}</div>
    </div>
  );
}

function SidePanel({ icon: Icon, title, children }) {
  return (
    <div className="rounded-md border border-line bg-panel shadow-sm">
      <div className="flex items-center gap-2 border-b border-divider px-4 py-2.5"><Icon className="h-4 w-4 text-navy" /><h3 className="font-serif text-sm font-semibold">{title}</h3></div>
      <div className="divide-y divide-divider px-4 py-1">{children}</div>
    </div>
  );
}

function PortfolioImpact({ analysisId, navigate }) {
  const [data, setData] = useState(null);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [savingNeeds, setSavingNeeds] = useState(false);
  const reload = useCallback(() => {
    Promise.all([api.get("/opportunities"), api.get("/portfolio/conflicts")])
      .then(([opps, conf]) => {
        const opp = opps.find((o) => o.analysis_id === analysisId);
        setData({ opp, conflicts: conf.conflicts, opps });
      }).catch(() => setData({ opp: null, conflicts: [], opps: [] }));
  }, [analysisId]);
  useEffect(() => { reload(); }, [reload]);
  if (!data) return null;

  const addToPortfolio = async () => {
    setAdding(true);
    try {
      const r = await api.post(`/analyses/${analysisId}/to-opportunity`, {});
      toast.success(r.created ? "Added to portfolio with AI-suggested resources" : "Already in your portfolio");
      reload();
    } catch (e) { toast.error(e.response?.data?.detail || "Could not add to portfolio"); }
    setAdding(false);
  };

  if (!data.opp) {
    return (
      <div className="rounded-md border-2 border-dashed border-navy/40 bg-navy/5 p-4">
        <div className="flex items-center gap-2"><Layers className="h-4 w-4 text-navy" /><h3 className="font-serif text-sm font-semibold">Portfolio impact</h3></div>
        <p className="mt-1 text-xs text-ink-muted">Add this tender to your portfolio to compare it against other opportunities and check for resource conflicts. BidPilot will suggest its resource needs (AI-inferred, editable).</p>
        <button data-testid="add-to-portfolio-btn" onClick={addToPortfolio} disabled={adding} className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-stamp px-3 py-1.5 text-xs font-semibold text-white hover:bg-stamp-dark disabled:opacity-60">
          {adding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Layers className="h-3.5 w-3.5" />} Add to Portfolio
        </button>
      </div>
    );
  }
  const opp = data.opp;
  const startEdit = () => {
    const r = opp.resources || {};
    setForm({ estimators: r.estimators ?? 0, engineers: r.engineers ?? 0, project_managers: r.project_managers ?? 0,
              specialist_engineers: r.specialist_engineers ?? 0, capital_cr: r.capital_cr ?? 0,
              bid_security_cr: r.bid_security_cr ?? 0, bid_effort_days: r.bid_effort_days ?? 0,
              value_cr: opp.value_cr ?? "" });
    setEditing(true);
  };
  const saveNeeds = async () => {
    setSavingNeeds(true);
    try {
      const resources = { ...(opp.resources || {}),
        estimators: Number(form.estimators) || 0, engineers: Number(form.engineers) || 0,
        project_managers: Number(form.project_managers) || 0, specialist_engineers: Number(form.specialist_engineers) || 0,
        capital_cr: Number(form.capital_cr) || 0, bid_security_cr: Number(form.bid_security_cr) || 0,
        bid_effort_days: Number(form.bid_effort_days) || 0 };
      const sources = { ...(opp.resource_sources || {}) };
      ["estimators", "engineers", "project_managers", "specialist_engineers", "capital_cr", "bid_security_cr", "bid_effort_days"].forEach((k) => { sources[k] = "USER_PROVIDED"; });
      const payload = { resources, resource_sources: sources };
      if (form.value_cr !== "") payload.value_cr = Number(form.value_cr);
      await api.patch(`/opportunities/${opp.id}`, payload);
      toast.success("Resource needs updated");
      setEditing(false); reload();
    } catch { toast.error("Failed to update needs"); }
    setSavingNeeds(false);
  };
  const related = data.conflicts.filter((c) => (c.opportunities || []).some((o) => o.id === opp.id));
  const others = new Set();
  related.forEach((c) => (c.opportunities || []).forEach((o) => { if (o.id !== opp.id) others.add(o.name); }));
  const impact = related.length >= 2 ? "HIGH" : related.length === 1 ? "MEDIUM" : "LOW";
  const impCls = { HIGH: "text-fail-text", MEDIUM: "text-review-text", LOW: "text-pass-text" };
  return (
    <div className="rounded-md border border-line bg-panel shadow-sm">
      <div className="flex items-center gap-2 border-b border-divider px-4 py-2.5"><Layers className="h-4 w-4 text-navy" /><h3 className="font-serif text-sm font-semibold">Portfolio impact</h3></div>
      <div className="space-y-2 px-4 py-3 text-sm">
        <div className="flex items-center justify-between"><span className="text-ink-muted">Impact</span><span className={`font-semibold ${impCls[impact]}`}>{impact}</span></div>
        <div className="flex items-center justify-between"><span className="text-ink-muted">Capital impact</span><span className="font-mono">₹{opp.resources?.capital_cr ?? 0} Cr</span></div>
        <div className="flex items-center justify-between"><span className="text-ink-muted">Estimators</span><span className="font-mono">{opp.resources?.estimators ?? 0}</span></div>
        {opp.resources?.specialist_engineers > 0 && <div className="flex items-center justify-between"><span className="text-ink-muted">Specialist eng.</span><span className="font-mono">{opp.resources.specialist_engineers}</span></div>}
        {others.size > 0 && (
          <div className="rounded-sm bg-review-bg px-2 py-1.5 text-xs text-review-text">Resource conflict with: {[...others].join(", ")}</div>
        )}
        {editing && (
          <div data-testid="edit-needs-form" className="rounded-md border border-navy/30 bg-navy/5 p-2">
            <div className="mb-1 flex items-center justify-between"><span className="font-mono text-[10px] uppercase tracking-wide text-navy">Edit resource needs</span></div>
            <div className="grid grid-cols-2 gap-1.5">
              {[["estimators", "Estimators"], ["specialist_engineers", "Specialists"], ["engineers", "Engineers"], ["project_managers", "PMs"], ["capital_cr", "Capital ₹Cr"], ["bid_security_cr", "Bid sec ₹Cr"], ["bid_effort_days", "Effort (d)"], ["value_cr", "Value ₹Cr"]].map(([k, l]) => (
                <label key={k} className="text-[10px] text-ink-muted">{l}
                  <input data-testid={`needs-${k}`} type="number" step="any" value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} className="mt-0.5 w-full rounded-sm border border-line px-1.5 py-1 font-mono text-xs outline-none focus:border-navy" />
                </label>
              ))}
            </div>
            <div className="mt-2 flex gap-2">
              <button data-testid="save-needs-btn" onClick={saveNeeds} disabled={savingNeeds} className="inline-flex items-center gap-1 rounded-md bg-navy px-2.5 py-1 text-xs font-semibold text-white hover:bg-navy-light disabled:opacity-60">{savingNeeds ? <Loader2 className="h-3 w-3 animate-spin" /> : null} Save needs</button>
              <button onClick={() => setEditing(false)} className="rounded-md border border-line px-2.5 py-1 text-xs font-semibold hover:bg-secondary">Cancel</button>
            </div>
          </div>
        )}
        <div className="flex flex-wrap gap-2 pt-1">
          {!editing && <button data-testid="edit-needs-btn" onClick={startEdit} className="rounded-md border border-navy px-2.5 py-1 text-xs font-semibold text-navy hover:bg-navy hover:text-white">Edit needs</button>}
          <button data-testid="pi-compare" onClick={() => navigate("/opportunities")} className="rounded-md border border-line px-2.5 py-1 text-xs font-semibold hover:bg-secondary">Compare</button>
          <button data-testid="pi-simulate" onClick={() => navigate("/portfolio")} className="rounded-md bg-navy px-2.5 py-1 text-xs font-semibold text-white hover:bg-navy-light">Simulate</button>
        </div>
      </div>
    </div>
  );
}

/* ---------------- REQUIREMENTS ---------------- */
function useFetch(path) {
  const [data, setData] = useState(null);
  useEffect(() => { api.get(path).then(setData).catch(() => setData([])); }, [path]);
  return data;
}

function ReqCard({ r, id }) {
  return (
    <div data-testid={`req-${r.id}`} className="rounded-md border border-line bg-panel p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{r.category}</span>
          </div>
          <h4 className="mt-0.5 font-medium text-ink">{r.name}</h4>
        </div>
        <StatusBadge status={r.status} testid={`req-status-${r.id}`} />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md border border-divider bg-paper/40 p-3">
          <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Tender says</div>
          <p className="mt-1 text-sm text-ink">{r.tender_requirement || r.description || "—"}</p>
        </div>
        <div className="rounded-md border border-divider bg-paper/40 p-3">
          <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Company says</div>
          <p className="mt-1 text-sm text-ink">{r.company_evidence || "—"}</p>
        </div>
      </div>
      {r.explanation && <p className="mt-2 text-xs text-ink-muted">{r.explanation}</p>}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SourceTag doc={r.evidence_source_document} page={r.source_page || r.evidence_source_page} />
          <Confidence value={r.confidence} />
        </div>
        <Link to={`/analyses/${id}/evidence/${r.id}`} data-testid={`open-evidence-${r.id}`} className="inline-flex items-center gap-1 text-sm font-medium text-navy hover:underline">
          <Eye className="h-3.5 w-3.5" /> Open evidence
        </Link>
      </div>
    </div>
  );
}

function Requirements({ id }) {
  const data = useFetch(`/analyses/${id}/requirements`);
  const [filter, setFilter] = useState("All");
  const [q, setQ] = useState("");
  if (!data) return <PageLoader label="Loading requirements" />;
  const filtered = data.filter((r) => (filter === "All" || r.status === filter) && (!q || (r.name + r.tender_requirement).toLowerCase().includes(q.toLowerCase())));
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input data-testid="req-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search requirements…" className="rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-navy" />
        {["All", "PASS", "FAIL", "NEEDS_REVIEW"].map((f) => (
          <button key={f} data-testid={`req-filter-${f}`} onClick={() => setFilter(f)} className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${filter === f ? "border-navy bg-navy text-white" : "border-line bg-panel text-ink-muted hover:bg-secondary"}`}>{f.replace("_", " ")}</button>
        ))}
      </div>
      <div className="space-y-3">
        {filtered.length === 0 ? <EmptyState title="No requirements match" /> : filtered.map((r) => <ReqCard key={r.id} r={r} id={id} />)}
      </div>
    </div>
  );
}

function Eligibility({ id }) {
  const data = useFetch(`/analyses/${id}/eligibility`);
  if (!data) return <PageLoader />;
  return <div className="space-y-3">{data.length === 0 ? <EmptyState title="No eligibility requirements found" /> : data.map((r) => <ReqCard key={r.id} r={r} id={id} />)}</div>;
}

function Technical({ id }) {
  const data = useFetch(`/analyses/${id}/technical`);
  if (!data) return <PageLoader />;
  return <div className="space-y-3">{data.length === 0 ? <EmptyState title="No technical requirements found" /> : data.map((r) => <ReqCard key={r.id} r={r} id={id} />)}</div>;
}

function Compliance({ id }) {
  const data = useFetch(`/analyses/${id}/compliance`);
  if (!data) return <PageLoader />;
  const groups = data.groups || { Available: [], Missing: [], "Needs Review": [] };
  const cfg = { Available: { icon: CheckCircle2, cls: "text-pass-text" }, Missing: { icon: XCircle, cls: "text-fail-text" }, "Needs Review": { icon: AlertTriangle, cls: "text-review-text" } };
  return (
    <div className="space-y-6">
      {Object.entries(groups).map(([g, items]) => {
        const { icon: Icon, cls } = cfg[g];
        return (
          <div key={g}>
            <div className="mb-2 flex items-center gap-2"><Icon className={`h-4 w-4 ${cls}`} /><h3 className="font-serif text-base font-semibold">{g}</h3><span className="font-mono text-xs text-ink-faint">({items.length})</span></div>
            {items.length === 0 ? <p className="text-sm text-ink-muted">None.</p> : <div className="space-y-3">{items.map((r) => <ReqCard key={r.id} r={r} id={id} />)}</div>}
          </div>
        );
      })}
    </div>
  );
}

function Risks({ id }) {
  const data = useFetch(`/analyses/${id}/risks`);
  const [sev, setSev] = useState("All");
  if (!data) return <PageLoader />;
  const filtered = data.filter((r) => sev === "All" || r.severity === sev);
  return (
    <div>
      <div className="mb-4 flex gap-2">
        {["All", "HIGH", "MEDIUM", "LOW"].map((s) => (
          <button key={s} data-testid={`risk-filter-${s}`} onClick={() => setSev(s)} className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${sev === s ? "border-navy bg-navy text-white" : "border-line bg-panel text-ink-muted hover:bg-secondary"}`}>{s}</button>
        ))}
      </div>
      <div className="space-y-3">
        {filtered.length === 0 ? <EmptyState icon={ShieldAlert} title="No risks in this category" /> : filtered.map((r) => (
          <div key={r.id} data-testid={`risk-${r.id}`} className="rounded-md border border-line bg-panel p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <h4 className="font-medium text-ink">{r.title}</h4>
              <SeverityBadge severity={r.severity} />
            </div>
            {r.clause && <p className="mt-1 font-mono text-xs text-navy">Clause: {r.clause}</p>}
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <div><span className="font-mono text-[10px] uppercase text-ink-faint">Concern</span><p className="text-sm text-ink-muted">{r.concern}</p></div>
              <div><span className="font-mono text-[10px] uppercase text-ink-faint">Impact</span><p className="text-sm text-ink-muted">{r.impact}</p></div>
            </div>
            <div className="mt-2"><SourceTag doc="Tender" page={r.source_page} /></div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Evidence({ id }) {
  const data = useFetch(`/analyses/${id}/evidence`);
  if (!data) return <PageLoader />;
  return (
    <div>
      <p className="mb-4 text-sm text-ink-muted">Every finding is traceable. Open any item to see the tender source and matching company evidence side by side.</p>
      <div className="space-y-3">
        {data.map((r) => (
          <Link key={r.id} to={`/analyses/${id}/evidence/${r.id}`} data-testid={`evidence-link-${r.id}`} className="flex items-center justify-between rounded-md border border-line bg-panel p-4 shadow-sm hover:bg-secondary/40">
            <div className="min-w-0">
              <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{r.category}</div>
              <div className="truncate font-medium">{r.name}</div>
              <div className="mt-1"><SourceTag doc={r.evidence_source_document} page={r.source_page || r.evidence_source_page} /></div>
            </div>
            <div className="flex items-center gap-3"><StatusBadge status={r.status} /><Eye className="h-4 w-4 text-navy" /></div>
          </Link>
        ))}
      </div>
    </div>
  );
}

/* ---------------- DECISION ---------------- */
function Decision({ analysis, id, navigate }) {
  const [payload, setPayload] = useState(null);
  const reqs = useFetch(`/analyses/${id}/requirements`);
  useEffect(() => { api.get(`/analyses/${id}/decision`).then(setPayload); }, [id]);
  if (!payload || !reqs) return <PageLoader />;
  const d = payload.decision || {};
  const passes = reqs.filter((r) => r.status === "PASS");
  const blocks = reqs.filter((r) => r.status === "FAIL");
  const reviews = reqs.filter((r) => r.status === "NEEDS_REVIEW");

  const exportReport = async () => {
    try {
      toast.info("Generating report…");
      const res = await api.raw.get(`/analyses/${id}/report`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `BidPilot - ${analysis.tender_name}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Report downloaded");
    } catch {
      toast.error("Could not generate report");
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="rounded-md border border-line bg-panel p-8 text-center shadow-sm paper-grid">
        <div className="font-mono text-[11px] uppercase tracking-widest text-ink-faint">BidPilot decision</div>
        <div className="mt-4 flex justify-center"><DecisionStamp outcome={d.outcome} size="xl" testid="decision-stamp-main" /></div>
        <div className="mt-6 flex justify-center"><ReadinessRing value={d.readiness_score} /></div>
        <div className="mx-auto mt-4 grid max-w-md grid-cols-2 gap-3">
          <ScoreBar label="Eligibility" value={d.eligibility} />
          <ScoreBar label="Compliance" value={d.compliance} />
          <ScoreBar label="Technical" value={d.technical} />
          <ScoreBar label="Risk" value={d.risk} />
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <DecList title="What passes" items={passes} icon={CheckCircle2} cls="text-pass-text" />
        <DecList title="What blocks" items={blocks} icon={XCircle} cls="text-fail-text" />
        <DecList title="Needs review" items={reviews} icon={AlertTriangle} cls="text-review-text" />
      </div>

      <div className="mt-5 rounded-md border border-line bg-panel p-5 shadow-sm">
        <h3 className="font-serif text-base font-semibold">Recommendation & next steps</h3>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">{d.recommendation}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={() => navigate(`/analyses/${id}/action-plan`)} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light"><ListTodo className="h-4 w-4" /> View Action Plan</button>
          <button data-testid="export-report-btn" onClick={exportReport} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold hover:bg-secondary"><Download className="h-4 w-4" /> Export report</button>
        </div>
      </div>

      <p className="mt-5 rounded-md border border-review-border bg-review-bg px-4 py-3 text-xs text-review-text">
        BidPilot provides decision support based on uploaded information. Final tender and legal decisions remain with your team.
      </p>
    </div>
  );
}

function DecList({ title, items, icon: Icon, cls }) {
  return (
    <div className="rounded-md border border-line bg-panel p-4 shadow-sm">
      <div className="flex items-center gap-2"><Icon className={`h-4 w-4 ${cls}`} /><h4 className="font-serif text-sm font-semibold">{title}</h4><span className="font-mono text-xs text-ink-faint">({items.length})</span></div>
      <ul className="mt-2 space-y-1 text-sm text-ink-muted">
        {items.length === 0 ? <li className="text-ink-faint">None</li> : items.map((r) => <li key={r.id} className="flex items-start gap-1.5"><span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${cls.replace("text", "bg")}`} />{r.name}</li>)}
      </ul>
    </div>
  );
}

/* ---------------- ACTION PLAN ---------------- */
function ActionPlan({ id }) {
  const [items, setItems] = useState(null);
  const [filter, setFilter] = useState("All");
  const load = useCallback(() => api.get(`/analyses/${id}/action-items`).then(setItems), [id]);
  useEffect(() => { load(); }, [load]);
  if (!items) return <PageLoader />;
  const toggle = async (it) => {
    const next = it.status === "OPEN" ? "DONE" : "OPEN";
    setItems((arr) => arr.map((x) => x.id === it.id ? { ...x, status: next } : x));
    try { await api.patch(`/action-items/${it.id}`, { status: next }); } catch { toast.error("Failed to update"); load(); }
  };
  const filtered = items.filter((it) => filter === "All" || (filter === "Open" ? it.status === "OPEN" : it.status === "DONE"));
  const prCls = { HIGH: "bg-fail-bg text-fail-text border-fail-border", MEDIUM: "bg-review-bg text-review-text border-review-border", LOW: "bg-secondary text-ink-muted border-line" };
  return (
    <div>
      <div className="mb-4 flex gap-2">
        {["All", "Open", "Done"].map((f) => (
          <button key={f} data-testid={`action-filter-${f}`} onClick={() => setFilter(f)} className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${filter === f ? "border-navy bg-navy text-white" : "border-line bg-panel text-ink-muted hover:bg-secondary"}`}>{f}</button>
        ))}
      </div>
      {filtered.length === 0 ? <EmptyState icon={ListTodo} title="No action items" description="Nothing to resolve in this view." /> : (
        <div className="space-y-2">
          {filtered.map((it) => (
            <div key={it.id} data-testid={`action-${it.id}`} className={`flex items-start gap-3 rounded-md border border-line bg-panel p-4 shadow-sm ${it.status === "DONE" ? "opacity-60" : ""}`}>
              <button data-testid={`action-toggle-${it.id}`} onClick={() => toggle(it)} className="mt-0.5">
                {it.status === "DONE" ? <CheckCircle2 className="h-5 w-5 text-pass-text" /> : <span className="block h-5 w-5 rounded-full border-2 border-line" />}
              </button>
              <div className="flex-1">
                <div className={`font-medium ${it.status === "DONE" ? "line-through" : ""}`}>{it.title}</div>
                <p className="text-sm text-ink-muted">{it.reason}</p>
                <div className="mt-1 font-mono text-xs text-ink-faint">{it.source}</div>
              </div>
              <span className={`rounded-sm border px-2 py-0.5 text-[10px] font-semibold ${prCls[it.priority]}`}>{it.priority}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
