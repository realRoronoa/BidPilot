import React, { useEffect, useState, useRef, useMemo } from "react";
import { FolderOpen, FileText, Trash2, UploadCloud, Search, Download, Loader2, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { fmtBytes, fmtDate } from "@/lib/format";
import { PageLoader, EmptyState } from "@/components/common";
import { toast } from "sonner";

const CATEGORIES = ["All", "Company Profile", "Experience", "Financial", "Registration", "Certification", "Personnel", "Equipment", "Other"];
const VS = { Verified: "text-pass-text", Processed: "text-ink-muted", "Needs Review": "text-review-text", Expired: "text-fail-text", Rejected: "text-fail-text" };

export default function Documents() {
  const [docs, setDocs] = useState(null);
  const [cat, setCat] = useState("All");
  const [q, setQ] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadCat, setUploadCat] = useState("Other");
  const ref = useRef();

  const load = () => api.get("/documents?doc_type=company").then(setDocs).catch(() => setDocs([]));
  useEffect(() => { load(); }, []);

  const filtered = useMemo(
    () => (docs || []).filter((d) => (cat === "All" || d.category === cat) && (!q || d.filename.toLowerCase().includes(q.toLowerCase()))),
    [docs, cat, q]
  );
  const expiringSoon = useMemo(
    () => (docs || []).filter((d) => d.expiry && new Date(d.expiry) < new Date(Date.now() + 60 * 86400000)),
    [docs]
  );

  if (!docs) return <PageLoader label="Loading documents" />;

  const upload = async (file) => {
    if (!file) return;
    setUploading(true);
    const fd = new FormData(); fd.append("file", file); fd.append("doc_type", "company"); fd.append("category", uploadCat);
    try { const res = await api.upload("/documents", fd); if (res.notice) toast.warning(res.notice); else toast.success("Uploaded"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Upload failed"); }
    setUploading(false);
  };

  const del = async (id) => { if (!window.confirm("Delete this document?")) return; try { await api.del(`/documents/${id}`); toast.success("Deleted"); load(); } catch { toast.error("Failed"); } };
  const download = (id) => window.open(`${api.raw.defaults.baseURL}/documents/${id}/download`, "_blank");


  return (
    <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><h1 className="font-serif text-2xl font-bold text-ink">Documents</h1><p className="mt-1 text-sm text-ink-muted">Your company evidence library.</p></div>
        <div className="flex items-center gap-2">
          <select data-testid="upload-category" value={uploadCat} onChange={(e) => setUploadCat(e.target.value)} className="rounded-md border border-line px-3 py-2 text-sm outline-none">
            {CATEGORIES.filter((c) => c !== "All").map((c) => <option key={c}>{c}</option>)}
          </select>
          <button data-testid="upload-doc-btn" onClick={() => ref.current?.click()} disabled={uploading} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light disabled:opacity-60">
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />} Upload
          </button>
          <input ref={ref} type="file" accept="application/pdf" hidden onChange={(e) => upload(e.target.files[0])} />
        </div>
      </div>

      {expiringSoon.length > 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-md border border-review-border bg-review-bg px-4 py-2.5 text-sm text-review-text">
          <AlertTriangle className="h-4 w-4" /> {expiringSoon.length} document(s) expiring within 60 days — review before your next bid.
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2"><Search className="h-4 w-4 text-ink-faint" /><input data-testid="doc-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search documents…" className="w-48 bg-transparent text-sm outline-none" /></div>
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((c) => <button key={c} data-testid={`doc-cat-${c}`} onClick={() => setCat(c)} className={`rounded-md border px-2.5 py-1.5 text-xs font-semibold ${cat === c ? "border-navy bg-navy text-white" : "border-line bg-panel text-ink-muted hover:bg-secondary"}`}>{c}</button>)}
        </div>
      </div>

      <div className="mt-4 rounded-md border border-line bg-panel shadow-sm">
        {filtered.length === 0 ? (
          <div className="p-5"><EmptyState icon={FolderOpen} title="No documents" description="Upload company evidence — profiles, financials, certificates, experience records." /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-divider text-left font-mono text-[11px] uppercase text-ink-faint">
                <th className="px-5 py-2.5">Document</th><th className="px-3 py-2.5">Category</th><th className="px-3 py-2.5">Uploaded</th><th className="px-3 py-2.5">Pages</th><th className="px-3 py-2.5">Size</th><th className="px-3 py-2.5">Expiry</th><th className="px-3 py-2.5">Status</th><th className="px-5 py-2.5" /></tr></thead>
              <tbody>{filtered.map((d) => (
                <tr key={d.id} data-testid={`doc-row-${d.id}`} className="border-b border-divider last:border-0 hover:bg-secondary/40">
                  <td className="px-5 py-3"><div className="flex items-center gap-2"><FileText className="h-4 w-4 text-navy" /><span className="font-medium">{d.filename}</span></div></td>
                  <td className="px-3 py-3 text-ink-muted">{d.category}</td>
                  <td className="px-3 py-3 font-mono text-xs text-ink-muted">{fmtDate(d.created_at)}</td>
                  <td className="px-3 py-3 font-mono text-xs">{d.page_count}</td>
                  <td className="px-3 py-3 font-mono text-xs">{fmtBytes(d.size)}</td>
                  <td className="px-3 py-3 font-mono text-xs text-ink-muted">{d.expiry || "—"}</td>
                  <td className="px-3 py-3"><span className={`text-xs font-semibold ${VS[d.verification_state] || "text-ink-muted"}`}>{d.verification_state || d.status}</span></td>
                  <td className="px-5 py-3 text-right"><div className="flex items-center justify-end gap-2">
                    <button data-testid={`download-${d.id}`} onClick={() => download(d.id)} className="text-ink-faint hover:text-navy"><Download className="h-4 w-4" /></button>
                    <button data-testid={`delete-doc-${d.id}`} onClick={() => del(d.id)} className="text-ink-faint hover:text-fail-text"><Trash2 className="h-4 w-4" /></button>
                  </div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
      <p className="mt-3 font-mono text-[11px] text-ink-faint">Documents are not automatically legally verified. "Verified" reflects manual confirmation only.</p>
    </div>
  );
}
