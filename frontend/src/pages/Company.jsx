import React, { useEffect, useState } from "react";
import { Building2, MapPin, CalendarRange, TrendingUp, Hammer, Users, Wrench, Award, FileBadge, Edit3, Save, X } from "lucide-react";
import { api } from "@/lib/api";
import { PageLoader, EmptyState, StatusBadge } from "@/components/common";
import { toast } from "sonner";

export default function Company() {
  const [c, setC] = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const load = () => api.get("/company").then((d) => { setC(d); if (d) setForm(d); }).catch(() => setC(false));
  useEffect(() => { load(); }, []);

  if (c === null) return <PageLoader label="Loading company" />;
  if (!c) return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <EmptyState icon={Building2} title="No company yet" description="Create a company profile so BidPilot can match tenders against your qualifications." />
    </div>
  );

  const save = async () => {
    try {
      await api.patch(`/company/${c.id}`, {
        legal_name: form.legal_name, registration: form.registration, location: form.location,
        years_experience: Number(form.years_experience) || 0, turnover: form.turnover, specialization: form.specialization,
      });
      toast.success("Company updated"); setEditing(false); load();
    } catch { toast.error("Failed to save"); }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-md bg-navy/10"><Building2 className="h-7 w-7 text-navy" /></div>
          <div>
            <h1 className="font-serif text-2xl font-bold text-ink">{c.legal_name}</h1>
            <p className="text-sm text-ink-muted">{c.specialization}</p>
          </div>
        </div>
        {!editing ? (
          <button data-testid="edit-company-btn" onClick={() => setEditing(true)} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold hover:bg-secondary"><Edit3 className="h-4 w-4" /> Edit</button>
        ) : (
          <div className="flex gap-2">
            <button data-testid="save-company-btn" onClick={save} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light"><Save className="h-4 w-4" /> Save</button>
            <button onClick={() => { setEditing(false); setForm(c); }} className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 text-sm font-semibold hover:bg-secondary"><X className="h-4 w-4" /></button>
          </div>
        )}
      </div>

      {/* Overview */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {editing ? (
          [["legal_name", "Legal name"], ["registration", "Registration"], ["location", "Location"], ["years_experience", "Years experience"], ["turnover", "Turnover"], ["specialization", "Specialization"]].map(([k, l]) => (
            <label key={k} className="rounded-md border border-line bg-panel p-3">
              <span className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">{l}</span>
              <input data-testid={`edit-${k}`} value={form[k] ?? ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} className="mt-1 w-full rounded-sm border border-line px-2 py-1 text-sm outline-none focus:border-navy" />
            </label>
          ))
        ) : (
          <>
            <Info icon={FileBadge} label="Registration" value={c.registration || "—"} />
            <Info icon={MapPin} label="Location" value={c.location || "—"} />
            <Info icon={CalendarRange} label="Experience" value={`${c.years_experience} years`} />
            <Info icon={TrendingUp} label="Turnover" value={c.turnover || "—"} />
            <Info icon={Award} label="Readiness" value={`${c.readiness || 0}%`} />
            <Info icon={Hammer} label="Specialization" value={c.specialization || "—"} />
          </>
        )}
      </div>

      {/* Registrations & certifications */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Section title="Registrations" icon={FileBadge}>
          {(c.registrations || []).length === 0 ? <Empty /> : (c.registrations || []).map((r, i) => (
            <Row key={`${r.number || r.name}-${i}`} main={r.name} sub={r.number} tail={r.valid_till ? `valid till ${r.valid_till}` : "—"} />
          ))}
        </Section>
        <Section title="Certifications" icon={Award}>
          {(c.certifications || []).length === 0 ? <Empty /> : (c.certifications || []).map((r, i) => (
            <div key={`${r.number || r.name}-${i}`} className="flex items-center justify-between py-2">
              <div><div className="text-sm font-medium">{r.name}</div><div className="font-mono text-xs text-ink-muted">{r.number} · exp {r.expiry}</div></div>
              <StatusBadge status={r.status} />
            </div>
          ))}
        </Section>
      </div>

      {/* Projects */}
      <Section title="Experience / Projects" icon={Hammer} className="mt-6">
        {(c.projects || []).length === 0 ? <Empty /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-divider text-left font-mono text-[11px] uppercase text-ink-faint"><th className="py-2 pr-3">Project</th><th className="py-2 pr-3">Client</th><th className="py-2 pr-3">Type</th><th className="py-2 pr-3">Value</th><th className="py-2 pr-3">Completed</th></tr></thead>
              <tbody>{c.projects.map((p) => (
                <tr key={p.id} className="border-b border-divider last:border-0"><td className="py-2 pr-3 font-medium">{p.name}</td><td className="py-2 pr-3 text-ink-muted">{p.client}</td><td className="py-2 pr-3 text-ink-muted">{p.project_type}</td><td className="py-2 pr-3 font-mono">{p.contract_value}</td><td className="py-2 pr-3 font-mono text-xs text-ink-muted">{p.completion_date}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </Section>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Section title="Key Personnel" icon={Users}>
          {(c.personnel || []).length === 0 ? <Empty /> : c.personnel.map((p) => (
            <Row key={p.id} main={`${p.name} · ${p.role}`} sub={`${p.qualification} · ${p.experience}`} tail={p.relevant} />
          ))}
        </Section>
        <Section title="Equipment" icon={Wrench}>
          {(c.equipment || []).length === 0 ? <Empty /> : c.equipment.map((e) => (
            <Row key={e.id} main={e.name} sub={`${e.capacity} · ${e.ownership}`} tail={e.availability} />
          ))}
        </Section>
      </div>
    </div>
  );
}

function Info({ icon: Icon, label, value }) {
  return (
    <div className="rounded-md border border-line bg-panel p-4 shadow-sm">
      <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wide text-ink-faint"><Icon className="h-3.5 w-3.5" /> {label}</div>
      <div className="mt-1 font-medium text-ink">{value}</div>
    </div>
  );
}
function Section({ title, icon: Icon, children, className = "" }) {
  return (
    <div className={`rounded-md border border-line bg-panel shadow-sm ${className}`}>
      <div className="flex items-center gap-2 border-b border-divider px-4 py-2.5"><Icon className="h-4 w-4 text-navy" /><h2 className="font-serif text-base font-semibold">{title}</h2></div>
      <div className="divide-y divide-divider px-4 py-1">{children}</div>
    </div>
  );
}
function Row({ main, sub, tail }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <div className="min-w-0"><div className="text-sm font-medium">{main}</div><div className="font-mono text-xs text-ink-muted">{sub}</div></div>
      <div className="shrink-0 text-right text-xs text-ink-muted">{tail}</div>
    </div>
  );
}
function Empty() { return <p className="py-4 text-sm text-ink-muted">No records yet.</p>; }
