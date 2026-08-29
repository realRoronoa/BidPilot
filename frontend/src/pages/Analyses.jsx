import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, FileSearch, Search, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate, decisionClass } from "@/lib/format";
import { PageLoader, EmptyState } from "@/components/common";
import { toast } from "sonner";

const FILTERS = ["All", "BID", "BID WITH CONDITIONS", "NO-BID"];

export default function Analyses() {
  const [items, setItems] = useState(null);
  const [filter, setFilter] = useState("All");
  const [q, setQ] = useState("");
  const [deleting, setDeleting] = useState(null);
  const navigate = useNavigate();

  const load = () => api.get("/analyses").then(setItems).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  if (!items) return <PageLoader label="Loading analyses" />;

  const filtered = items.filter((a) => {
    const matchF = filter === "All" || a.decision === filter;
    const matchQ = !q || (a.tender_name + a.company_name).toLowerCase().includes(q.toLowerCase());
    return matchF && matchQ;
  });

  const del = async (id) => {
    if (!window.confirm("Delete this analysis? This cannot be undone.")) return;
    setDeleting(id);
    try { await api.del(`/analyses/${id}`); toast.success("Analysis deleted"); load(); }
    catch { toast.error("Failed to delete"); }
    setDeleting(null);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-bold text-ink">My Analyses</h1>
          <p className="mt-1 text-sm text-ink-muted">Every tender you've qualified with BidPilot.</p>
        </div>
        <Link to="/analyses/new" data-testid="analyses-new-btn" className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-light">
          <Plus className="h-4 w-4" /> New Analysis
        </Link>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2">
          <Search className="h-4 w-4 text-ink-faint" />
          <input data-testid="analyses-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tenders…" className="w-56 bg-transparent text-sm outline-none" />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((f) => (
            <button key={f} data-testid={`filter-${f}`} onClick={() => setFilter(f)}
              className={`rounded-md border px-3 py-2 text-xs font-semibold transition-colors ${filter === f ? "border-navy bg-navy text-white" : "border-line bg-panel text-ink-muted hover:bg-secondary"}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 rounded-md border border-line bg-panel shadow-sm">
        {filtered.length === 0 ? (
          <div className="p-5">
            <EmptyState icon={FileSearch} title="No analyses found"
              description={items.length === 0 ? "Start by creating your first analysis." : "No analyses match your filters."}
              action={<Link to="/analyses/new" className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light"><Plus className="h-4 w-4" /> New Analysis</Link>} />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-divider text-left font-mono text-[11px] uppercase tracking-wide text-ink-faint">
                  <th className="px-5 py-2.5 font-medium">Tender</th>
                  <th className="px-3 py-2.5 font-medium">Company</th>
                  <th className="px-3 py-2.5 font-medium">Date</th>
                  <th className="px-3 py-2.5 font-medium">Readiness</th>
                  <th className="px-3 py-2.5 font-medium">Decision</th>
                  <th className="px-3 py-2.5 font-medium">Issues</th>
                  <th className="px-5 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr key={a.id} data-testid={`analysis-row-${a.id}`} className="border-b border-divider last:border-0 hover:bg-secondary/50">
                    <td className="px-5 py-3 font-medium text-ink">
                      <button onClick={() => navigate(`/analyses/${a.id}`)} className="text-left hover:text-navy">{a.tender_name}</button>
                    </td>
                    <td className="px-3 py-3 text-ink-muted">{a.company_name}</td>
                    <td className="px-3 py-3 font-mono text-xs text-ink-muted">{fmtDate(a.date)}</td>
                    <td className="px-3 py-3 font-mono font-semibold">{a.readiness != null ? `${a.readiness}%` : "—"}</td>
                    <td className="px-3 py-3">
                      {a.decision ? <span className={`inline-block rounded-sm border px-2 py-0.5 text-[11px] font-semibold ${decisionClass(a.decision)}`}>{a.decision}</span>
                        : <span className="font-mono text-xs text-stamp">{a.status}</span>}
                    </td>
                    <td className="px-3 py-3 font-mono">{a.issues || 0}</td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link to={`/analyses/${a.id}`} className="text-sm font-medium text-navy hover:underline">Open</Link>
                        <button data-testid={`delete-${a.id}`} onClick={() => del(a.id)} className="text-ink-faint hover:text-fail-text">
                          {deleting === a.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
