import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { FileText, ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { PageLoader, StatusBadge, Confidence, SourceTag } from "@/components/common";

export default function EvidenceViewer() {
  const { id, eid } = useParams();
  const [data, setData] = useState(null);
  const [side, setSide] = useState("tender");
  useEffect(() => { api.get(`/analyses/${id}/evidence/${eid}`).then(setData).catch(() => setData(false)); }, [id, eid]);
  if (data === null) return <PageLoader label="Loading evidence" />;
  if (data === false) return <div className="p-8">Evidence not found.</div>;
  const r = data.requirement;
  const pane = side === "tender" ? data.tender : data.company;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <Link to={`/analyses/${id}/evidence`} className="inline-flex items-center gap-1 font-mono text-xs text-navy hover:underline"><ArrowLeft className="h-3.5 w-3.5" /> Back to evidence</Link>
      <h1 className="mt-2 font-serif text-2xl font-bold">{r.name}</h1>
      <div className="mt-1 flex items-center gap-3"><span className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{r.category}</span><StatusBadge status={r.status} /><Confidence value={r.confidence} /></div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {/* Document viewer */}
        <div className="rounded-md border border-line bg-panel shadow-sm">
          <div className="flex items-center justify-between border-b border-divider px-4 py-2.5">
            <div className="flex gap-1">
              <button data-testid="viewer-tender-tab" onClick={() => setSide("tender")} className={`rounded-sm px-3 py-1 text-xs font-semibold ${side === "tender" ? "bg-navy text-white" : "text-ink-muted hover:bg-secondary"}`}>Tender source</button>
              <button data-testid="viewer-company-tab" onClick={() => setSide("company")} className={`rounded-sm px-3 py-1 text-xs font-semibold ${side === "company" ? "bg-navy text-white" : "text-ink-muted hover:bg-secondary"}`}>Company source</button>
            </div>
          </div>
          <div className="p-4">
            <div className="flex items-center gap-2 rounded-t-md border border-line bg-paper px-3 py-2">
              <FileText className="h-4 w-4 text-navy" />
              <span className="truncate font-mono text-xs">{pane.filename || "No source document"}</span>
              {pane.page && <span className="ml-auto font-mono text-xs text-ink-muted">page {pane.page}{pane.page_count ? ` / ${pane.page_count}` : ""}</span>}
            </div>
            <div className="min-h-[320px] rounded-b-md border border-t-0 border-line bg-[#fbfaf7] p-5">
              {pane.page_text ? (
                <p className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-ink">{pane.page_text}</p>
              ) : (
                <div className="flex h-full min-h-[280px] flex-col items-center justify-center text-center text-ink-faint">
                  <FileText className="h-8 w-8" strokeWidth={1.25} />
                  <p className="mt-2 max-w-xs text-sm">{side === "company" ? "No specific company source page was matched for this item." : "Source page text not available."}</p>
                </div>
              )}
            </div>
            <p className="mt-2 font-mono text-[11px] text-ink-faint">Extracted source text (page-level). Exact-pixel highlighting is not shown to avoid fabricated highlights.</p>
          </div>
        </div>

        {/* Explanation */}
        <div className="space-y-4">
          <ExpBlock label="Tender requirement" value={r.tender_requirement || r.description} />
          <ExpBlock label="Tender evidence" value={data.tender.page_text ? `Page ${data.tender.page}` : "—"} sub={data.tender.filename} />
          <ExpBlock label="Company evidence" value={r.company_evidence} />
          <div className="rounded-md border border-line bg-panel p-4 shadow-sm">
            <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Conclusion</div>
            <div className="mt-1 flex items-center gap-2"><StatusBadge status={r.status} /><Confidence value={r.confidence} /></div>
            <p className="mt-2 text-sm text-ink-muted">{r.explanation}</p>
            <div className="mt-3"><SourceTag doc={r.evidence_source_document} page={r.evidence_source_page || r.source_page} /></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ExpBlock({ label, value, sub }) {
  return (
    <div className="rounded-md border border-line bg-panel p-4 shadow-sm">
      <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{label}</div>
      <p className="mt-1 text-sm text-ink">{value || "—"}</p>
      {sub && <p className="mt-0.5 font-mono text-xs text-ink-muted">{sub}</p>}
    </div>
  );
}
