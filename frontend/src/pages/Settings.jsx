import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { User, Building, Bell, Lock, CreditCard, Save, Loader2, Monitor } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageLoader } from "@/components/common";
import { toast } from "sonner";

const SECTIONS = [
  { key: "profile", label: "Profile", icon: User },
  { key: "workspace", label: "Workspace", icon: Building },
  { key: "notifications", label: "Notifications", icon: Bell },
  { key: "security", label: "Security", icon: Lock },
  { key: "billing", label: "Billing", icon: CreditCard },
];

export default function Settings() {
  const { section } = useParams();
  const navigate = useNavigate();
  const { user, setUser } = useAuth();
  const active = SECTIONS.find((s) => s.key === section) ? section : "profile";
  const [data, setData] = useState(null);
  const [profile, setProfile] = useState({ name: "" });
  const [workspace, setWorkspace] = useState({ name: "", timezone: "" });
  const [saving, setSaving] = useState(false);
  const [notif, setNotif] = useState({ analysis: true, deadlines: true, expiry: true, findings: true });

  useEffect(() => { api.get("/settings").then((d) => { setData(d); setProfile({ name: d.profile.name }); setWorkspace({ name: d.workspace?.name || "", timezone: d.workspace?.timezone || "UTC" }); }); }, []);
  if (!data) return <PageLoader label="Loading settings" />;

  const saveProfile = async () => { setSaving(true); try { await api.patch("/settings/profile", profile); setUser({ ...user, name: profile.name }); toast.success("Profile updated"); } catch { toast.error("Failed"); } setSaving(false); };
  const saveWorkspace = async () => { setSaving(true); try { await api.patch("/settings/workspace", workspace); toast.success("Workspace updated"); } catch { toast.error("Failed"); } setSaving(false); };

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 md:px-8">
      <h1 className="font-serif text-2xl font-bold">Settings</h1>
      <div className="mt-5 grid gap-6 md:grid-cols-[200px_1fr]">
        <nav className="space-y-1">
          {SECTIONS.map((s) => (
            <button key={s.key} data-testid={`settings-tab-${s.key}`} onClick={() => navigate(`/settings/${s.key}`)} className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${active === s.key ? "bg-navy text-white" : "text-ink-muted hover:bg-secondary"}`}>
              <s.icon className="h-4 w-4" /> {s.label}
            </button>
          ))}
        </nav>

        <div className="rounded-md border border-line bg-panel p-6 shadow-sm">
          {active === "profile" && (
            <div className="max-w-md space-y-4">
              <h2 className="font-serif text-lg font-semibold">Profile</h2>
              <Field label="Full name"><input data-testid="settings-name" value={profile.name} onChange={(e) => setProfile({ name: e.target.value })} className="fld2" /></Field>
              <Field label="Email"><input value={data.profile.email} disabled className="fld2 opacity-70" /></Field>
              <Field label="Role"><input value={data.profile.role} disabled className="fld2 opacity-70" /></Field>
              <button data-testid="save-profile" onClick={saveProfile} disabled={saving} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light disabled:opacity-60">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save</button>
            </div>
          )}
          {active === "workspace" && (
            <div className="max-w-md space-y-4">
              <h2 className="font-serif text-lg font-semibold">Workspace</h2>
              <Field label="Workspace name"><input data-testid="settings-ws-name" value={workspace.name} onChange={(e) => setWorkspace({ ...workspace, name: e.target.value })} className="fld2" /></Field>
              <Field label="Timezone"><input data-testid="settings-ws-tz" value={workspace.timezone} onChange={(e) => setWorkspace({ ...workspace, timezone: e.target.value })} className="fld2" /></Field>
              <button data-testid="save-workspace" onClick={saveWorkspace} disabled={saving} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light disabled:opacity-60">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save</button>
            </div>
          )}
          {active === "notifications" && (
            <div className="max-w-md">
              <h2 className="font-serif text-lg font-semibold">Notification preferences</h2>
              <div className="mt-4 space-y-3">
                {[["analysis", "Analysis completion"], ["deadlines", "Tender deadlines"], ["expiry", "Document expiry"], ["findings", "Important findings"]].map(([k, l]) => (
                  <label key={k} className="flex items-center justify-between rounded-md border border-divider bg-paper/40 px-4 py-3">
                    <span className="text-sm font-medium">{l}</span>
                    <input data-testid={`notif-pref-${k}`} type="checkbox" checked={notif[k]} onChange={(e) => setNotif({ ...notif, [k]: e.target.checked })} className="h-4 w-4 accent-navy" />
                  </label>
                ))}
              </div>
              <button onClick={() => toast.success("Preferences saved")} className="mt-4 inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light"><Save className="h-4 w-4" /> Save</button>
            </div>
          )}
          {active === "security" && (
            <div className="max-w-md space-y-4">
              <h2 className="font-serif text-lg font-semibold">Security</h2>
              <Field label="Current password"><input type="password" className="fld2" placeholder="••••••••" /></Field>
              <Field label="New password"><input type="password" className="fld2" placeholder="••••••••" /></Field>
              <button data-testid="change-password" onClick={() => toast.success("Password change requested (demo)")} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light"><Lock className="h-4 w-4" /> Update password</button>
              <div className="mt-4 rounded-md border border-divider bg-paper/40 p-4">
                <div className="flex items-center gap-2 text-sm font-medium"><Monitor className="h-4 w-4 text-navy" /> Active session</div>
                <p className="mt-1 font-mono text-xs text-ink-muted">This browser · signed in via secure cookie</p>
              </div>
            </div>
          )}
          {active === "billing" && (
            <div>
              <h2 className="font-serif text-lg font-semibold">Billing</h2>
              <p className="mt-2 text-sm text-ink-muted">Manage your subscription, usage and invoices on the billing page.</p>
              <Link to="/billing" data-testid="goto-billing" className="mt-4 inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light"><CreditCard className="h-4 w-4" /> Open Billing</Link>
            </div>
          )}
        </div>
      </div>
      <style>{`.fld2{width:100%;border:1px solid #D1D5DB;border-radius:6px;background:#fff;padding:0.55rem 0.75rem;font-size:0.875rem;outline:none}.fld2:focus{border-color:#1A365D;box-shadow:0 0 0 3px rgba(26,54,93,0.12)}`}</style>
    </div>
  );
}

function Field({ label, children }) {
  return <label className="block"><span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>{children}</label>;
}
