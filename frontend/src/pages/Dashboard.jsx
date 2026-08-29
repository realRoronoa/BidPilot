import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Plus, FileSearch, CheckCircle2, AlertTriangle, XCircle, ListTodo, CalendarClock,
  FileWarning, ArrowRight, Activity, TrendingUp, Layers,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate, relTime, decisionClass } from "@/lib/format";
import { PageLoader, EmptyState } from "@/components/common";

function Stat({ icon: Icon, label, value, accent, testid }) {
  return (
    <div data-testid={testid} className="rounded-md border border-line bg-panel p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</span>
        <Icon className={`h-4 w-4 ${accent || "text-navy"}`} strokeWidth={1.75} />
      </div>
      <div className="mt-2 font-serif text-3xl font-bold text-ink">{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/dashboard").then(setData).catch((e) => setErr(e.message));
    api.get("/portfolio/summary").then(setPortfolio).catch(() => setPortfolio(null));
  }, []);

  if (err) return <div className="p-8 text-fail-text">Failed to load dashboard: {err}</div>;
  if (!data) return <PageLoader label="Loading dashboard" />;

  const s = data.stats;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-bold text-ink">Dashboard</h1>
          <p className="mt-1 text-sm text-ink-muted">What needs your attention today.</p>
        </div>
        <Link to="/analyses/new" data-testid="dashboard-new-analysis"
          className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-light">
          <Plus className="h-4 w-4" /> New Analysis
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat icon={FileSearch} label="Total analyses" value={s.total} testid="stat-total" />        <Stat icon={Activity} label="Active" value={s.active} accent="text-stamp" testid="stat-active" />
        <Stat icon={CheckCircle2} label="Bids" value={s.bids} accent="text-pass-text" testid="stat-bids" />
        <Stat icon={AlertTriangle} label="Conditional" value={s.conditional} accent="text-review-text" testid="stat-conditional" />
        <Stat icon={XCircle} label="No-bids" value={s.nobids} accent="text-fail-text" testid="stat-nobids" />
        <Stat icon={ListTodo} label="Open actions" value={s.open_actions} testid="stat-actions" />
        <Stat icon={CalendarClock} label="Upcoming deadlines" value={s.upcoming_deadlines} testid="stat-deadlines" />
        <Stat icon={FileWarning} label="Docs to review" value={s.docs_attention} accent="text-review-text" testid="stat-docs" />
      </div>

      {portfolio && portfolio.total > 0 && (
        <Link to="/portfolio" data-testid="portfolio-banner" className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-md border border-navy/30 bg-navy/5 p-4 transition-colors hover:bg-navy/10">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-navy text-white"><Layers className="h-5 w-5" /></div>
            <div>
              <div className="font-serif text-base font-semibold text-ink">Portfolio intelligence</div>
              <div className="text-sm text-ink-muted">Across {portfolio.total} opportunities, your capacity supports pursuing <b className="text-pass-text">{portfolio.pursue}</b> · {portfolio.watch} watch · {portfolio.defer} defer · <b className="text-stamp">{portfolio.conflicts}</b> resource conflicts</div>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 text-sm font-semibold text-navy">Open optimizer <ArrowRight className="h-4 w-4" /></span>
        </Link>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Recent analyses */}
        <div className="lg:col-span-2">
          <div className="rounded-md border border-line bg-panel shadow-sm">
            <div className="flex items-center justify-between border-b border-divider px-5 py-3">
              <h2 className="font-serif text-base font-semibold">Recent analyses</h2>
              <Link to="/analyses" className="inline-flex items-center gap-1 text-sm font-medium text-navy hover:underline">
                View all <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
            {data.recent_analyses.length === 0 ? (
              <div className="p-5">
                <EmptyState icon={FileSearch} title="No analyses yet"
                  description="Upload a tender and your company evidence to get your first bid/no-bid recommendation."
                  action={<Link to="/analyses/new" className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light"><Plus className="h-4 w-4" /> New Analysis</Link>} />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-divider text-left font-mono text-[11px] uppercase tracking-wide text-ink-faint">
                      <th className="px-5 py-2.5 font-medium">Tender</th>
                      <th className="px-3 py-2.5 font-medium">Date</th>
                      <th className="px-3 py-2.5 font-medium">Readiness</th>
                      <th className="px-3 py-2.5 font-medium">Decision</th>
                      <th className="px-3 py-2.5 font-medium">Issues</th>
                      <th className="px-5 py-2.5" />
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_analyses.map((a) => (
                      <tr key={a.id} data-testid={`recent-row-${a.id}`} className="border-b border-divider last:border-0 hover:bg-secondary/50">
                        <td className="px-5 py-3">
                          <div className="font-medium text-ink">{a.tender_name}</div>
                          <div className="text-xs text-ink-muted">{a.company_name}</div>
                        </td>
                        <td className="px-3 py-3 font-mono text-xs text-ink-muted">{fmtDate(a.date)}</td>
                        <td className="px-3 py-3 font-mono font-semibold">{a.readiness != null ? `${a.readiness}%` : "—"}</td>
                        <td className="px-3 py-3">
                          {a.decision ? <span className={`inline-block rounded-sm border px-2 py-0.5 text-[11px] font-semibold ${decisionClass(a.decision)}`}>{a.decision}</span>
                            : <span className="font-mono text-xs text-stamp">{a.status}</span>}
                        </td>
                        <td className="px-3 py-3 font-mono text-sm">{a.issues || 0}</td>
                        <td className="px-5 py-3 text-right">
                          <Link to={`/analyses/${a.id}`} className="text-sm font-medium text-navy hover:underline">Open</Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          <div className="rounded-md border border-line bg-panel shadow-sm">
            <div className="border-b border-divider px-5 py-3"><h2 className="font-serif text-base font-semibold">Upcoming deadlines</h2></div>
            <div className="divide-y divide-divider">
              {data.deadlines.length === 0 ? <p className="px-5 py-6 text-sm text-ink-muted">No upcoming deadlines.</p> :
                data.deadlines.map((d, i) => (
                  <Link to={`/analyses/${d.analysis_id}`} key={`${d.analysis_id}-${d.label}-${i}`} className="flex items-start gap-3 px-5 py-3 hover:bg-secondary/50">
                    <CalendarClock className="mt-0.5 h-4 w-4 shrink-0 text-stamp" />
                    <div>
                      <div className="text-sm font-medium">{d.label}</div>
                      <div className="font-mono text-xs text-ink-muted">{fmtDate(d.date)} · {d.tender}</div>
                    </div>
                  </Link>
                ))}
            </div>
          </div>

          <div className="rounded-md border border-line bg-panel shadow-sm">
            <div className="border-b border-divider px-5 py-3"><h2 className="font-serif text-base font-semibold">Recent activity</h2></div>
            <div className="divide-y divide-divider">
              {data.activity.length === 0 ? <p className="px-5 py-6 text-sm text-ink-muted">No activity yet.</p> :
                data.activity.map((e) => (
                  <div key={e.id} className="flex items-start gap-3 px-5 py-3">
                    <TrendingUp className="mt-0.5 h-4 w-4 shrink-0 text-navy" />
                    <div>
                      <div className="text-sm">{e.detail}</div>
                      <div className="font-mono text-xs text-ink-muted">{e.actor} · {relTime(e.created_at)}</div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
