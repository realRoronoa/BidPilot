import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Layers, Sparkles, TriangleAlert, Loader2, CheckCircle2, ArrowRight, FlaskConical,
  RotateCcw, PlusCircle, MinusCircle, Gauge, Download, Save, Trash2, Bookmark, GitCompare,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { PageLoader, EmptyState, RiskPill, BucketBadge } from "@/components/common";
import { toast } from "sonner";

const OBJECTIVES = [
  { key: "balanced", label: "Balanced" },
  { key: "value", label: "Max value" },
  { key: "qualification", label: "Max qualification" },
  { key: "risk", label: "Min risk" },
  { key: "strategic", label: "Max strategic fit" },
];

export default function Portfolio() {
  const [objective, setObjective] = useState("value");
  const [result, setResult] = useState(null);
  const [conflicts, setConflicts] = useState(null);
  const [cap, setCap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scenario, setScenario] = useState(null);
  const [overrides, setOverrides] = useState({});
  const [simLoading, setSimLoading] = useState(false);
  const [scenarios, setScenarios] = useState([]);
  const [scenarioName, setScenarioName] = useState("");
  const [cmpLeft, setCmpLeft] = useState("baseline");
  const [cmpRight, setCmpRight] = useState("");
  const [cmpResult, setCmpResult] = useState(null);

  const loadScenarios = useCallback(() => api.get("/portfolio/scenarios").then(setScenarios).catch(() => {}), []);

  const optimize = useCallback(async (obj) => {
    setLoading(true);
    try {
      const r = await api.post("/portfolio/optimize", { objective: obj });
      setResult(r.baseline);
    } catch (e) {
      setResult(false);
      if (e.response?.status !== 400) toast.error("Optimization failed");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    api.get("/portfolio/conflicts").then((d) => { setConflicts(d.conflicts); setCap(d.capacity); }).catch(() => setConflicts([]));
    loadScenarios();
  }, [loadScenarios]);
  useEffect(() => { optimize(objective); }, [objective, optimize]);

  const runScenario = async () => {
    const active = Object.fromEntries(Object.entries(overrides).filter(([, v]) => v !== "" && v != null));
    if (Object.keys(active).length === 0) { toast.error("Change at least one constraint first"); return; }
    setSimLoading(true);
    try {
      const r = await api.post("/portfolio/optimize", { objective, overrides: active });
      setScenario(r);
    } catch { toast.error("Scenario failed"); }
    setSimLoading(false);
  };
  const resetScenario = () => { setScenario(null); setOverrides({}); };

  const saveScenario = async () => {
    const active = Object.fromEntries(Object.entries(overrides).filter(([, v]) => v !== "" && v != null));
    if (!scenarioName.trim()) { toast.error("Name your scenario first"); return; }
    if (Object.keys(active).length === 0) { toast.error("Change a constraint to save"); return; }
    try { await api.post("/portfolio/scenarios", { name: scenarioName.trim(), objective, overrides: active }); toast.success("Scenario saved"); setScenarioName(""); loadScenarios(); }
    catch { toast.error("Failed to save scenario"); }
  };
  const applyScenario = async (sc) => {
    setObjective(sc.objective); setOverrides(sc.overrides);
    setSimLoading(true);
    try { const r = await api.post("/portfolio/optimize", { objective: sc.objective, overrides: sc.overrides }); setScenario(r); toast.success(`Loaded "${sc.name}"`); }
    catch { toast.error("Failed to load scenario"); }
    setSimLoading(false);
  };
  const deleteScenario = async (id) => { try { await api.del(`/portfolio/scenarios/${id}`); loadScenarios(); } catch { toast.error("Failed"); } };
  const compareScenarios = async () => {
    if (!cmpRight) { toast.error("Pick a scenario to compare"); return; }
    try { setCmpResult(await api.post("/portfolio/scenarios/compare", { left_id: cmpLeft, right_id: cmpRight, objective })); }
    catch (e) { toast.error(e.response?.data?.detail || "Compare failed"); }
  };
  const downloadReport = async () => {
    try {
      toast.info("Generating portfolio report…");
      const res = await api.raw.get(`/portfolio/report?objective=${objective}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const link = document.createElement("a"); link.href = url; link.download = "BidPilot - Portfolio.pdf";
      document.body.appendChild(link); link.click(); link.remove(); window.URL.revokeObjectURL(url);
      toast.success("Report downloaded");
    } catch { toast.error("Could not generate report"); }
  };

  if (loading && !result) return <PageLoader label="Optimizing portfolio" />;

  const base = cap ? {
    specialist_engineers: cap.people?.specialist_engineers,
    estimators: cap.people?.estimators,
    working_capital_cr: cap.finance?.working_capital_cr,
  } : {};

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-md bg-navy/10"><Layers className="h-6 w-6 text-navy" /></div>
          <div><h1 className="font-serif text-2xl font-bold text-ink">Portfolio Optimizer</h1><p className="mt-0.5 text-sm text-ink-muted">Choose the projects your team can realistically pursue together.</p></div>
        </div>
        <div className="flex items-center gap-2">
          <button data-testid="portfolio-report-btn" onClick={downloadReport} className="inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-xs font-semibold hover:bg-secondary"><Download className="h-3.5 w-3.5" /> Report</button>
          <span className="hidden font-mono text-[11px] uppercase text-ink-faint sm:block">Objective</span>
          <div className="flex flex-wrap gap-1">
            {OBJECTIVES.map((o) => (
              <button key={o.key} data-testid={`objective-${o.key}`} onClick={() => setObjective(o.key)}
                className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${objective === o.key ? "border-navy bg-navy text-white" : "border-line bg-panel text-ink-muted hover:bg-secondary"}`}>{o.label}</button>
            ))}
          </div>
        </div>
      </div>

      {result === false || !result ? (
        <div className="mt-6"><EmptyState icon={Layers} title="No opportunities to optimize" description="Add opportunities to your pipeline first."
          action={<Link to="/opportunities" className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light">Go to Opportunities</Link>} /></div>
      ) : (
        <>
          {/* KPIs */}
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Recommended to pursue" value={result.pursue.length} accent="text-pass-text" testid="kpi-pursue" />
            <Kpi label="Watch / conditional" value={result.watch.length} accent="text-review-text" testid="kpi-watch" />
            <Kpi label="Defer / skip" value={result.defer.length} accent="text-fail-text" testid="kpi-defer" />
            <Kpi label="Resource conflicts" value={conflicts ? conflicts.length : "—"} accent="text-stamp" testid="kpi-conflicts" />
          </div>

          {/* Capacity utilization */}
          {result.totals && (
            <div className="mt-4 rounded-md border border-line bg-panel p-4 shadow-sm">
              <div className="mb-3 flex items-center gap-2"><Gauge className="h-4 w-4 text-navy" /><h3 className="font-serif text-sm font-semibold">Recommended portfolio uses</h3></div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {Object.entries(result.totals).filter(([k]) => k !== "count").map(([k, v]) => (
                  <Meter key={k} label={k.replace(/_/g, " ")} used={v.used} limit={v.limit} />
                ))}
              </div>
            </div>
          )}

          {result.no_feasible_reason && (
            <div className="mt-4 rounded-md border border-fail-border bg-fail-bg p-4" data-testid="no-feasible">
              <div className="flex items-center gap-2 font-semibold text-fail-text"><TriangleAlert className="h-4 w-4" /> No feasible portfolio</div>
              <p className="mt-1 text-sm text-fail-text">{result.no_feasible_reason.message}</p>
              {result.no_feasible_reason.constraint && <p className="mt-1 font-mono text-xs text-fail-text">Primary constraint: {result.no_feasible_reason.constraint} — required {result.no_feasible_reason.required}, available {result.no_feasible_reason.available}</p>}
            </div>
          )}

          {/* Buckets */}
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            <BucketColumn title="Pursue" bucket="PURSUE" items={result.pursue} />
            <BucketColumn title="Watch / Conditional" bucket="WATCH" items={result.watch} />
            <BucketColumn title="Defer / Skip" bucket="DEFER" items={result.defer} />
          </div>

          {/* Conflicts */}
          <h2 className="mt-8 font-serif text-xl font-semibold">Resource conflicts</h2>
          <div className="mt-2 space-y-2">
            {!conflicts || conflicts.length === 0 ? <p className="text-sm text-ink-muted">No resource conflicts detected.</p> :
              conflicts.map((c, i) => (
                <div key={i} data-testid={`conflict-${i}`} className="rounded-md border border-review-border bg-review-bg/50 p-4">
                  <div className="flex items-center gap-2 font-semibold text-review-text"><TriangleAlert className="h-4 w-4" /> {c.resource}
                    {c.available != null && <span className="font-mono text-xs">· need {c.required} / have {c.available}</span>}</div>
                  <p className="mt-1 text-sm text-ink-muted">{c.message}</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {c.opportunities.map((o) => <span key={o.id} className="rounded-sm border border-line bg-panel px-2 py-0.5 font-mono text-[11px]">{o.name} <span className="text-ink-faint">({o.requires})</span></span>)}
                  </div>
                </div>
              ))}
          </div>

          {/* What-if simulator */}
          <div className="mt-8 rounded-md border-2 border-dashed border-navy/40 bg-navy/5 p-5">
            <div className="flex items-center gap-2"><FlaskConical className="h-5 w-5 text-navy" /><h2 className="font-serif text-xl font-semibold">What-If Simulator</h2></div>
            <p className="mt-1 text-sm text-ink-muted">Temporarily change a constraint and see how the recommendation shifts. Your saved capacity is never modified.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <SimField label="Specialist engineers" k="specialist_engineers" base={base.specialist_engineers} overrides={overrides} setOverrides={setOverrides} />
              <SimField label="Estimators" k="estimators" base={base.estimators} overrides={overrides} setOverrides={setOverrides} />
              <SimField label="Working capital (₹Cr)" k="working_capital_cr" base={base.working_capital_cr} overrides={overrides} setOverrides={setOverrides} step="0.5" />
            </div>
            <div className="mt-4 flex gap-2">
              <button data-testid="run-scenario-btn" onClick={runScenario} disabled={simLoading} className="inline-flex items-center gap-2 rounded-md bg-stamp px-4 py-2 text-sm font-semibold text-white hover:bg-stamp-dark disabled:opacity-60">
                {simLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Recalculate
              </button>
              {scenario && <button data-testid="reset-scenario-btn" onClick={resetScenario} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold hover:bg-secondary"><RotateCcw className="h-4 w-4" /> Reset</button>}
            </div>

            {/* Save & saved scenarios */}
            <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-navy/15 pt-4">
              <input data-testid="scenario-name" value={scenarioName} onChange={(e) => setScenarioName(e.target.value)} placeholder="Name this scenario…" className="rounded-md border border-line px-3 py-1.5 text-sm outline-none focus:border-navy" />
              <button data-testid="save-scenario-btn" onClick={saveScenario} className="inline-flex items-center gap-1.5 rounded-md border border-navy px-3 py-1.5 text-sm font-semibold text-navy hover:bg-navy hover:text-white"><Save className="h-4 w-4" /> Save scenario</button>
            </div>
            {scenarios.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2" data-testid="saved-scenarios">
                {scenarios.map((sc) => (
                  <div key={sc.id} className="flex items-center gap-1 rounded-md border border-line bg-panel px-2 py-1 text-xs">
                    <Bookmark className="h-3.5 w-3.5 text-navy" />
                    <button data-testid={`load-scenario-${sc.id}`} onClick={() => applyScenario(sc)} className="font-medium hover:text-navy">{sc.name}</button>
                    <button data-testid={`del-scenario-${sc.id}`} onClick={() => deleteScenario(sc.id)} className="ml-1 text-ink-faint hover:text-fail-text"><Trash2 className="h-3 w-3" /></button>
                  </div>
                ))}
              </div>
            )}

            {scenarios.length > 0 && (
              <div className="mt-4 border-t border-navy/15 pt-4" data-testid="scenario-compare">
                <div className="flex items-center gap-2"><GitCompare className="h-4 w-4 text-navy" /><h3 className="font-serif text-sm font-semibold">Compare two scenarios</h3></div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <select data-testid="cmp-left" value={cmpLeft} onChange={(e) => setCmpLeft(e.target.value)} className="rounded-md border border-line bg-panel px-2 py-1.5 text-sm outline-none">
                    <option value="baseline">Baseline (saved capacity)</option>
                    {scenarios.map((sc) => <option key={sc.id} value={sc.id}>{sc.name}</option>)}
                  </select>
                  <span className="font-mono text-xs text-ink-faint">vs</span>
                  <select data-testid="cmp-right" value={cmpRight} onChange={(e) => setCmpRight(e.target.value)} className="rounded-md border border-line bg-panel px-2 py-1.5 text-sm outline-none">
                    <option value="">Select scenario…</option>
                    <option value="baseline">Baseline (saved capacity)</option>
                    {scenarios.map((sc) => <option key={sc.id} value={sc.id}>{sc.name}</option>)}
                  </select>
                  <button data-testid="compare-scenarios-btn" onClick={compareScenarios} className="inline-flex items-center gap-1.5 rounded-md bg-navy px-3 py-1.5 text-sm font-semibold text-white hover:bg-navy-light"><GitCompare className="h-4 w-4" /> Compare</button>
                </div>
                {cmpResult && (
                  <div className="mt-3" data-testid="scenario-compare-result">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <ScenarioCol side={cmpResult.left} />
                      <ScenarioCol side={cmpResult.right} />
                    </div>
                    <div className="mt-2 grid gap-2 sm:grid-cols-3 text-xs">
                      <DiffBox label="Only in left" items={cmpResult.only_left} cls="text-fail-text" />
                      <DiffBox label="In both" items={cmpResult.common} cls="text-ink-muted" />
                      <DiffBox label="Only in right" items={cmpResult.only_right} cls="text-pass-text" />
                    </div>
                  </div>
                )}
              </div>
            )}

            {scenario && (
              <div className="mt-5 grid gap-4 lg:grid-cols-2" data-testid="scenario-result">
                <div className="rounded-md border border-line bg-panel p-4">
                  <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Current</div>
                  <div className="mt-1 text-sm font-medium">{result.pursue.map((o) => o.name).join("  +  ") || "None"}</div>
                </div>
                <div className="rounded-md border border-pass-border bg-pass-bg p-4">
                  <div className="font-mono text-[10px] uppercase tracking-wide text-pass-text">Scenario</div>
                  <div className="mt-1 text-sm font-medium text-pass-text">{scenario.scenario.pursue.map((o) => o.name).join("  +  ") || "None"}</div>
                </div>
                <div className="lg:col-span-2 rounded-md border border-line bg-panel p-4">
                  <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">What changed</div>
                  <div className="mt-2 space-y-1 text-sm">
                    {scenario.diff.added.length === 0 && scenario.diff.removed.length === 0 && <div className="text-ink-muted">No change to the recommended portfolio.</div>}
                    {scenario.diff.added.map((a) => <div key={a.id} className="flex items-center gap-2 text-pass-text"><PlusCircle className="h-4 w-4" /> Added <b>{a.name}</b></div>)}
                    {scenario.diff.removed.map((r) => <div key={r.id} className="flex items-center gap-2 text-fail-text"><MinusCircle className="h-4 w-4" /> Removed <b>{r.name}</b></div>)}
                  </div>
                  <p className="mt-2 font-mono text-[11px] text-ink-faint">Modeled capacity effect only — this does not guarantee bid success.</p>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({ label, value, accent, testid }) {
  return (
    <div data-testid={testid} className="rounded-md border border-line bg-panel p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</div>
      <div className={`mt-1 font-serif text-3xl font-bold ${accent}`}>{value}</div>
    </div>
  );
}

function Meter({ label, used, limit }) {
  const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const near = pct >= 90;
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs"><span className="capitalize text-ink-muted">{label}</span><span className="font-mono font-semibold">{used}/{limit}</span></div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-divider"><div className={`h-full rounded-full ${near ? "bg-stamp" : "bg-navy"}`} style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

function BucketColumn({ title, bucket, items }) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-2"><BucketBadge bucket={bucket} testid={`bucket-${bucket}`} /><h3 className="font-serif text-base font-semibold">{title}</h3><span className="font-mono text-xs text-ink-faint">({items.length})</span></div>
      <div className="space-y-3">
        {items.length === 0 ? <p className="text-sm text-ink-muted">None.</p> : items.map((o) => (
          <div key={o.id} data-testid={`rec-${o.id}`} className="rounded-md border border-line bg-panel p-4 shadow-sm">
            <div className="flex items-start justify-between gap-2">
              <div><div className="font-medium text-ink">{o.name}</div><div className="text-xs text-ink-muted">{o.client}{o.value_cr != null ? ` · ₹${o.value_cr} Cr` : ""}</div></div>
              <RiskPill risk={o.risk} />
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="font-mono font-semibold text-navy">{o.qualification_fit}% fit</span>
              {o.deadline && <span className="font-mono text-ink-muted">· due {fmtDate(o.deadline)}</span>}
            </div>
            {bucket === "PURSUE" && (
              <ul className="mt-2 space-y-0.5 text-xs text-ink-muted">{o.reasons.map((r, i) => <li key={i} className="flex items-start gap-1.5"><CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-pass-text" />{r}</li>)}</ul>
            )}
            {o.note && bucket !== "PURSUE" && <p className="mt-2 rounded-sm bg-secondary/60 px-2 py-1 text-xs text-ink-muted">{o.note}</p>}
            {o.constraints?.length > 0 && bucket === "PURSUE" && <div className="mt-2 font-mono text-[10px] text-ink-faint">Needs: {o.constraints.join(" · ")}</div>}
            {o.analysis_id && <Link to={`/analyses/${o.analysis_id}`} className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-navy hover:underline">View analysis <ArrowRight className="h-3 w-3" /></Link>}
          </div>
        ))}
      </div>
    </div>
  );
}

function ScenarioCol({ side }) {
  return (
    <div className="rounded-md border border-line bg-panel p-3">
      <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{side.name}</div>
      <div className="mt-0.5 font-mono text-[10px] text-ink-faint">obj: {side.objective}{Object.keys(side.overrides || {}).length ? ` · ${Object.entries(side.overrides).map(([k, v]) => `${k}=${v}`).join(", ")}` : ""}</div>
      <div className="mt-2 space-y-1 text-sm">
        {side.pursue.length === 0 ? <div className="text-ink-muted">No feasible portfolio</div> :
          side.pursue.map((o) => <div key={o.id} className="flex items-start gap-1.5"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-pass-text" />{o.name}</div>)}
      </div>
    </div>
  );
}

function DiffBox({ label, items, cls }) {
  return (
    <div className="rounded-md border border-divider bg-paper/40 p-2">
      <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{label}</div>
      {items.length === 0 ? <div className="mt-0.5 text-ink-faint">—</div> : items.map((o) => <div key={o.id} className={`mt-0.5 ${cls}`}>{o.name}</div>)}
    </div>
  );
}

function SimField({ label, k, base, overrides, setOverrides, step = "1" }) {
  const val = overrides[k] ?? "";
  return (
    <label className="rounded-md border border-line bg-panel p-3">
      <div className="flex items-center justify-between"><span className="text-xs font-medium text-ink-muted">{label}</span><span className="font-mono text-[10px] text-ink-faint">now: {base ?? "—"}</span></div>
      <input data-testid={`sim-${k}`} type="number" step={step} placeholder={`${base ?? ""}`} value={val}
        onChange={(e) => setOverrides((o) => ({ ...o, [k]: e.target.value === "" ? "" : Number(e.target.value) }))}
        className="mt-1 w-full rounded-sm border border-line px-2 py-1.5 font-mono text-sm outline-none focus:border-navy" />
    </label>
  );
}
