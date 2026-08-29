import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Briefcase, Layers, GitCompare, Trash2, ArrowRight, X } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { PageLoader, EmptyState, RiskPill } from "@/components/common";
import { toast } from "sonner";

const STAGES = ["DISCOVERED", "ANALYZING", "REVIEW", "READY", "BID", "SUBMITTED", "AWARDED", "DEFERRED", "NO-BID"];
const STAGE_CLS = {
  DISCOVERED: "bg-secondary text-ink-muted", ANALYZING: "bg-navy/10 text-navy", REVIEW: "bg-review-bg text-review-text",
  READY: "bg-pass-bg text-pass-text", BID: "bg-pass-bg text-pass-text", SUBMITTED: "bg-navy/10 text-navy",
  AWARDED: "bg-pass-bg text-pass-text", DEFERRED: "bg-fail-bg text-fail-text", "NO-BID": "bg-fail-bg text-fail-text",
};

export default function Opportunities() {
  const [items, setItems] = useState(null);
  const [sel, setSel] = useState({});
  const [compare, setCompare] = useState(null);

  const load = () => api.get("/opportunities").then(setItems).catch(() => setItems([]));
  useEffect(() => { load(); }, []);
  if (!items) return <PageLoader label="Loading opportunities" />;

  const selectedIds = Object.keys(sel).filter((k) => sel[k]);
  const changeStage = async (o, stage) => {
    setItems((arr) => arr.map((x) => x.id === o.id ? { ...x, stage } : x));
    try { await api.patch(`/opportunities/${o.id}`, { stage }); } catch { toast.error("Failed"); load(); }
  };
  const del = async (id) => { if (!window.confirm("Remove this opportunity?")) return; try { await api.del(`/opportunities/${id}`); toast.success("Removed"); load(); } catch { toast.error("Failed"); } };
  const runCompare = async () => {
    if (selectedIds.length < 2) { toast.error("Select at least two opportunities"); return; }
    try { setCompare(await api.post("/portfolio/compare", { opportunity_ids: selectedIds })); } catch (e) { toast.error(e.response?.data?.detail || "Compare failed"); }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-md bg-navy/10"><Briefcase className="h-6 w-6 text-navy" /></div>
          <div><h1 className="font-serif text-2xl font-bold text-ink">Opportunity Pipeline</h1><p className="mt-0.5 text-sm text-ink-muted">Every project you could bid on. Select a few to compare, or optimize the whole portfolio.</p></div>
        </div>
        <div className="flex gap-2">
          <button data-testid="compare-btn" onClick={runCompare} disabled={selectedIds.length < 2} className="inline-flex items-center gap-2 rounded-md border border-navy px-4 py-2.5 text-sm font-semibold text-navy hover:bg-navy hover:text-white disabled:opacity-40">
            <GitCompare className="h-4 w-4" /> Compare ({selectedIds.length})
          </button>
          <Link to="/portfolio" className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-light"><Layers className="h-4 w-4" /> Optimize Portfolio</Link>
        </div>
      </div>

      <div className="mt-5 rounded-md border border-line bg-panel shadow-sm">
        {items.length === 0 ? (
          <div className="p-5"><EmptyState icon={Briefcase} title="No opportunities yet" description="Run a tender analysis or add opportunities to build your pipeline." /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-divider text-left font-mono text-[11px] uppercase text-ink-faint">
                <th className="px-4 py-2.5"></th><th className="px-3 py-2.5">Opportunity</th><th className="px-3 py-2.5">Value</th>
                <th className="px-3 py-2.5">Qual fit</th><th className="px-3 py-2.5">Risk</th><th className="px-3 py-2.5">Deadline</th>
                <th className="px-3 py-2.5">Stage</th><th className="px-4 py-2.5"></th></tr></thead>
              <tbody>{items.map((o) => (
                <tr key={o.id} data-testid={`opp-row-${o.id}`} className="border-b border-divider last:border-0 hover:bg-secondary/40">
                  <td className="px-4 py-3"><input type="checkbox" data-testid={`opp-check-${o.id}`} checked={!!sel[o.id]} onChange={(e) => setSel((s) => ({ ...s, [o.id]: e.target.checked }))} className="h-4 w-4 accent-navy" /></td>
                  <td className="px-3 py-3"><div className="font-medium text-ink">{o.name}</div><div className="text-xs text-ink-muted">{o.client} · {o.location}</div></td>
                  <td className="px-3 py-3 font-mono">{o.value_cr != null ? `₹${o.value_cr} Cr` : "—"}</td>
                  <td className="px-3 py-3 font-mono font-semibold">{o.qualification_fit}%</td>
                  <td className="px-3 py-3"><RiskPill risk={o.risk} /></td>
                  <td className="px-3 py-3 font-mono text-xs text-ink-muted">{fmtDate(o.deadline)}</td>
                  <td className="px-3 py-3">
                    <select data-testid={`opp-stage-${o.id}`} value={o.stage} onChange={(e) => changeStage(o, e.target.value)} className={`rounded-sm border-0 px-2 py-1 text-[11px] font-semibold outline-none ${STAGE_CLS[o.stage] || "bg-secondary"}`}>
                      {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-right"><div className="flex items-center justify-end gap-2">
                    {o.analysis_id && <Link to={`/analyses/${o.analysis_id}`} className="text-sm font-medium text-navy hover:underline">Analysis</Link>}
                    <button data-testid={`opp-del-${o.id}`} onClick={() => del(o.id)} className="text-ink-faint hover:text-fail-text"><Trash2 className="h-4 w-4" /></button>
                  </div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>

      {compare && <CompareModal data={compare} onClose={() => setCompare(null)} />}
    </div>
  );
}

function CompareModal({ data, onClose }) {
  const opps = data.opportunities;
  const highlight = (id) => id === data.best_value_id || id === data.best_lowrisk_id || id === data.best_qualification_id;
  const rows = [
    ["Qualification", (o) => `${o.qualification_fit}%`],
    ["Risk", (o) => o.risk],
    ["Value", (o) => o.value_cr != null ? `₹${o.value_cr} Cr` : "—"],
    ["Capital", (o) => `₹${o.resources?.capital_cr ?? 0} Cr`],
    ["Estimators", (o) => o.resources?.estimators ?? 0],
    ["Specialist eng.", (o) => o.resources?.specialist_engineers ?? 0],
    ["Bid effort (d)", (o) => o.resources?.bid_effort_days ?? 0],
    ["Deadline", (o) => o.deadline || "—"],
  ];
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="compare-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative max-h-[85vh] w-full max-w-4xl overflow-auto rounded-md border border-line bg-panel p-6 shadow-xl scrollbar-thin">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-xl font-bold">Opportunity Comparison</h2>
          <button data-testid="compare-close" onClick={onClose} className="rounded-md p-1 hover:bg-secondary"><X className="h-5 w-5" /></button>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr><th className="px-3 py-2 text-left font-mono text-[11px] uppercase text-ink-faint"></th>
              {opps.map((o) => <th key={o.id} className="px-3 py-2 text-left font-medium">{o.name}</th>)}</tr></thead>
            <tbody>{rows.map(([label, fn]) => (
              <tr key={label} className="border-t border-divider"><td className="px-3 py-2 font-mono text-[11px] uppercase text-ink-faint">{label}</td>
                {opps.map((o) => <td key={o.id} className="px-3 py-2 font-mono">{fn(o)}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Best label="Best individual (value)" id={data.best_value_id} opps={opps} />
          <Best label="Best low-risk" id={data.best_lowrisk_id} opps={opps} />
          <Best label="Best qualification" id={data.best_qualification_id} opps={opps} />
        </div>
        <div className="mt-3 rounded-md border border-pass-border bg-pass-bg p-4">
          <div className="font-mono text-[10px] uppercase tracking-wide text-pass-text">Best combined portfolio</div>
          <div className="mt-1 font-medium text-pass-text">{data.best_portfolio_detail.map((o) => o.name).join("  +  ") || "None feasible together"}</div>
        </div>
      </div>
    </div>
  );
}
function Best({ label, id, opps }) {
  const o = opps.find((x) => x.id === id);
  return <div className="rounded-md border border-line bg-paper/40 p-3"><div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{label}</div><div className="mt-1 text-sm font-medium">{o?.name}</div></div>;
}
