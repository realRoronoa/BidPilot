import React, { useEffect, useState } from "react";
import { Bell, CheckCheck, FileCheck2, CalendarClock, FileWarning, XCircle, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { relTime } from "@/lib/format";
import { PageLoader, EmptyState } from "@/components/common";

const ICONS = { analysis_complete: FileCheck2, analysis_failed: XCircle, deadline: CalendarClock, document_expiring: FileWarning, action_item: AlertTriangle, blocker: AlertTriangle };

export default function Notifications() {
  const [items, setItems] = useState(null);
  const load = () => api.get("/notifications").then(setItems).catch(() => setItems([]));
  useEffect(() => { load(); }, []);
  if (!items) return <PageLoader label="Loading notifications" />;

  const markAll = async () => { await api.post("/notifications/read-all", {}); load(); };
  const markOne = async (id) => { await api.patch(`/notifications/${id}`, {}); load(); };
  const unread = items.filter((n) => !n.read).length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 md:px-8">
      <div className="flex items-center justify-between">
        <div><h1 className="font-serif text-2xl font-bold">Notifications</h1><p className="mt-1 text-sm text-ink-muted">{unread} unread</p></div>
        {unread > 0 && <button data-testid="mark-all-read" onClick={markAll} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold hover:bg-secondary"><CheckCheck className="h-4 w-4" /> Mark all read</button>}
      </div>
      <div className="mt-5 space-y-2">
        {items.length === 0 ? <EmptyState icon={Bell} title="No notifications" description="Analysis updates, deadlines and document alerts will appear here." /> :
          items.map((n) => {
            const Icon = ICONS[n.type] || Bell;
            return (
              <button key={n.id} data-testid={`notif-${n.id}`} onClick={() => markOne(n.id)} className={`flex w-full items-start gap-3 rounded-md border p-4 text-left shadow-sm ${n.read ? "border-line bg-panel" : "border-navy/30 bg-navy/5"}`}>
                <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${n.read ? "text-ink-faint" : "text-navy"}`} />
                <div className="flex-1"><div className="flex items-center gap-2"><span className="font-medium">{n.title}</span>{!n.read && <span className="h-2 w-2 rounded-full bg-stamp" />}</div><p className="text-sm text-ink-muted">{n.message}</p><div className="mt-1 font-mono text-xs text-ink-faint">{relTime(n.created_at)}</div></div>
              </button>
            );
          })}
      </div>
    </div>
  );
}
