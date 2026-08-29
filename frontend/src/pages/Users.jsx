import React, { useEffect, useState } from "react";
import { Users as UsersIcon, UserPlus, Loader2, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { relTime } from "@/lib/format";
import { PageLoader } from "@/components/common";
import { toast } from "sonner";

const ROLES = ["Owner", "Admin", "Bid Manager", "Member", "Viewer"];
const ROLE_DESC = {
  Owner: "Full control incl. billing", Admin: "Manage workspace & users", "Bid Manager": "Create & run analyses",
  Member: "Contribute to analyses", Viewer: "Read-only access",
};

export default function Users() {
  const [members, setMembers] = useState(null);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "Member" });
  const [inviting, setInviting] = useState(false);
  const load = () => api.get("/workspace/users").then(setMembers).catch(() => setMembers([]));
  useEffect(() => { load(); }, []);
  if (!members) return <PageLoader label="Loading users" />;

  const invite = async () => {
    if (!form.email || !form.name) { toast.error("Name and email required"); return; }
    setInviting(true);
    try { await api.post("/workspace/users/invite", form); toast.success("Invitation sent"); setShow(false); setForm({ name: "", email: "", role: "Member" }); load(); }
    catch { toast.error("Failed to invite"); }
    setInviting(false);
  };
  const changeRole = async (m, role) => { setMembers((arr) => arr.map((x) => x.id === m.id ? { ...x, role } : x)); try { await api.patch(`/workspace/users/${m.id}`, { role }); } catch { toast.error("Failed"); load(); } };

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 md:px-8">
      <div className="flex items-center justify-between">
        <div><h1 className="font-serif text-2xl font-bold">Users & Roles</h1><p className="mt-1 text-sm text-ink-muted">Manage who can access this workspace.</p></div>
        <button data-testid="invite-user-btn" onClick={() => setShow((s) => !s)} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light"><UserPlus className="h-4 w-4" /> Invite user</button>
      </div>

      {show && (
        <div className="mt-4 rounded-md border border-line bg-panel p-4 shadow-sm">
          <div className="grid gap-3 sm:grid-cols-3">
            <input data-testid="invite-name" placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-navy" />
            <input data-testid="invite-email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-navy" />
            <select data-testid="invite-role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="rounded-md border border-line px-3 py-2 text-sm outline-none">{ROLES.map((r) => <option key={r}>{r}</option>)}</select>
          </div>
          <button data-testid="send-invite" onClick={invite} disabled={inviting} className="mt-3 inline-flex items-center gap-2 rounded-md bg-stamp px-4 py-2 text-sm font-semibold text-white hover:bg-stamp-dark disabled:opacity-60">{inviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />} Send invitation</button>
        </div>
      )}

      <div className="mt-5 rounded-md border border-line bg-panel shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-divider text-left font-mono text-[11px] uppercase text-ink-faint"><th className="px-5 py-2.5">Name</th><th className="px-3 py-2.5">Email</th><th className="px-3 py-2.5">Role</th><th className="px-3 py-2.5">Status</th><th className="px-3 py-2.5">Last activity</th></tr></thead>
            <tbody>{members.map((m) => (
              <tr key={m.id} data-testid={`member-${m.id}`} className="border-b border-divider last:border-0">
                <td className="px-5 py-3"><div className="flex items-center gap-2"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-navy font-mono text-[10px] font-semibold text-white">{m.name?.split(" ").map((p) => p[0]).slice(0, 2).join("")}</span><span className="font-medium">{m.name}</span></div></td>
                <td className="px-3 py-3 font-mono text-xs text-ink-muted">{m.email}</td>
                <td className="px-3 py-3">
                  <select data-testid={`role-${m.id}`} value={m.role} onChange={(e) => changeRole(m, e.target.value)} disabled={m.role === "Owner"} className="rounded-sm border border-line bg-panel px-2 py-1 text-xs outline-none disabled:opacity-70">{ROLES.map((r) => <option key={r}>{r}</option>)}</select>
                </td>
                <td className="px-3 py-3"><span className={`rounded-sm px-2 py-0.5 text-xs font-semibold ${m.status === "Active" ? "bg-pass-bg text-pass-text" : "bg-review-bg text-review-text"}`}>{m.status}</span></td>
                <td className="px-3 py-3 font-mono text-xs text-ink-muted">{m.last_activity ? relTime(m.last_activity) : "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>

      <div className="mt-5 rounded-md border border-line bg-panel p-4 shadow-sm">
        <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-navy" /><h3 className="font-serif text-sm font-semibold">Role permissions</h3></div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{ROLES.map((r) => <div key={r} className="rounded-md border border-divider bg-paper/40 p-3"><div className="text-sm font-medium">{r}</div><div className="text-xs text-ink-muted">{ROLE_DESC[r]}</div></div>)}</div>
      </div>
    </div>
  );
}
