import React, { useEffect, useState } from "react";
import { Gauge, Save, Loader2, Users, Wallet, Wrench, Clock, Plus, Trash2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { PageLoader, SourceBadge } from "@/components/common";
import { toast } from "sonner";

const SOURCES = ["VERIFIED", "USER_PROVIDED", "AI_EXTRACTED", "AI_INFERRED", "ASSUMPTION", "NEEDS_REVIEW"];
const PEOPLE = [["estimators", "Estimators"], ["bid_managers", "Bid managers"], ["engineers", "Engineers"], ["project_managers", "Project managers"], ["specialist_engineers", "Specialist engineers"]];
const FINANCE = [["working_capital_cr", "Working capital (₹Cr)"], ["bid_security_capacity_cr", "Bid-security capacity (₹Cr)"]];
const TIME = [["bid_team_capacity_days", "Bid-team capacity (days)"], ["current_workload_days", "Current workload (days)"]];

export default function Capacity() {
  const [cap, setCap] = useState(null);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);

  useEffect(() => { api.get("/capacity").then(setCap).catch(() => setCap(false)); }, []);
  if (cap === null) return <PageLoader label="Loading capacity" />;
  if (!cap) return <div className="p-8">Failed to load capacity.</div>;

  const setField = (group, key, val) => setCap((c) => ({ ...c, [group]: { ...c[group], [key]: val } }));
  const setSource = (key, val) => setCap((c) => ({ ...c, sources: { ...(c.sources || {}), [key]: val } }));
  const setEquip = (i, patch) => setCap((c) => ({ ...c, equipment: c.equipment.map((e, idx) => idx === i ? { ...e, ...patch } : e) }));
  const addEquip = () => setCap((c) => ({ ...c, equipment: [...c.equipment, { name: "New equipment", total: 1, committed: 0 }] }));
  const delEquip = (i) => setCap((c) => ({ ...c, equipment: c.equipment.filter((_, idx) => idx !== i) }));

  const save = async () => {
    setSaving(true);
    try {
      await api.raw.put("/capacity", { people: cap.people, finance: cap.finance, equipment: cap.equipment, time: cap.time, sources: cap.sources });
      toast.success("Capacity saved");
    } catch { toast.error("Failed to save capacity"); }
    setSaving(false);
  };

  const suggest = async () => {
    setSuggesting(true);
    try {
      const { suggestion } = await api.post("/capacity/suggest", {});
      setCap((c) => {
        const people = { ...c.people, ...(suggestion.people || {}) };
        const sources = { ...(c.sources || {}) };
        Object.keys(suggestion.people || {}).forEach((k) => { sources[k] = "AI_INFERRED"; });
        let equipment = c.equipment;
        if (Array.isArray(suggestion.equipment) && suggestion.equipment.length) {
          const existing = new Set(c.equipment.map((e) => e.name.toLowerCase()));
          const add = suggestion.equipment.filter((e) => e.name && !existing.has(e.name.toLowerCase()))
            .map((e) => ({ name: e.name, total: e.total || 1, committed: 0 }));
          equipment = [...c.equipment, ...add];
          add.forEach((e) => { sources[e.name] = "AI_INFERRED"; });
        }
        return { ...c, people, equipment, sources };
      });
      toast.success("Suggested values from your documents — review and save. All marked AI-inferred.");
    } catch (e) { toast.error(e.response?.data?.detail || "Could not infer capacity"); }
    setSuggesting(false);
  };

  const Num = ({ group, k, label }) => (
    <div className="rounded-md border border-line bg-panel p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-ink-muted">{label}</span>
        <SourceBadge source={cap.sources?.[k]} />
      </div>
      <input data-testid={`cap-${k}`} type="number" step="any" value={cap[group][k] ?? 0} onChange={(e) => setField(group, k, Number(e.target.value))}
        className="mt-1 w-full rounded-sm border border-line px-2 py-1.5 font-mono text-sm outline-none focus:border-navy" />
      <select value={cap.sources?.[k] || "USER_PROVIDED"} onChange={(e) => setSource(k, e.target.value)} className="mt-1 w-full rounded-sm border border-line bg-panel px-1 py-1 font-mono text-[10px] outline-none">
        {SOURCES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
      </select>
    </div>
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 md:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-md bg-navy/10"><Gauge className="h-6 w-6 text-navy" /></div>
          <div><h1 className="font-serif text-2xl font-bold text-ink">Capacity Manager</h1><p className="mt-0.5 text-sm text-ink-muted">The people, money, equipment and time your team can realistically commit to bidding.</p></div>
        </div>
        <div className="flex items-center gap-2">
          <button data-testid="suggest-capacity-btn" onClick={suggest} disabled={suggesting} className="inline-flex items-center gap-2 rounded-md border border-navy px-4 py-2.5 text-sm font-semibold text-navy hover:bg-navy hover:text-white disabled:opacity-60">
            {suggesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Suggest from evidence
          </button>
          <button data-testid="save-capacity-btn" onClick={save} disabled={saving} className="inline-flex items-center gap-2 rounded-md bg-navy px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-light disabled:opacity-60">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save capacity
          </button>
        </div>
      </div>

      <Section icon={Users} title="People">
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">{PEOPLE.map(([k, l]) => <Num key={k} group="people" k={k} label={l} />)}</div>
      </Section>
      <Section icon={Wallet} title="Financial capacity">
        <div className="grid gap-3 sm:grid-cols-2">{FINANCE.map(([k, l]) => <Num key={k} group="finance" k={k} label={l} />)}</div>
      </Section>
      <Section icon={Wrench} title="Equipment" action={<button data-testid="add-equip-btn" onClick={addEquip} className="inline-flex items-center gap-1 rounded-md border border-navy px-2.5 py-1 text-xs font-semibold text-navy hover:bg-navy hover:text-white"><Plus className="h-3.5 w-3.5" /> Add</button>}>
        <div className="space-y-2">
          {cap.equipment.length === 0 ? <p className="text-sm text-ink-muted">No equipment configured.</p> : cap.equipment.map((e, i) => (
            <div key={i} className="grid grid-cols-1 items-center gap-2 rounded-md border border-line bg-panel p-2 sm:grid-cols-[2fr_1fr_1fr_1fr_auto]">
              <input data-testid={`equip-name-${i}`} value={e.name} onChange={(ev) => setEquip(i, { name: ev.target.value })} className="rounded-sm border border-line px-2 py-1 text-sm outline-none focus:border-navy" />
              <label className="text-xs text-ink-muted">Total <input type="number" value={e.total} onChange={(ev) => setEquip(i, { total: Number(ev.target.value) })} className="mt-0.5 w-full rounded-sm border border-line px-2 py-1 font-mono text-sm outline-none" /></label>
              <label className="text-xs text-ink-muted">Committed <input type="number" value={e.committed} onChange={(ev) => setEquip(i, { committed: Number(ev.target.value) })} className="mt-0.5 w-full rounded-sm border border-line px-2 py-1 font-mono text-sm outline-none" /></label>
              <div className="text-xs text-ink-muted">Available <div className="mt-0.5 font-mono text-sm font-semibold text-navy">{Math.max(0, (e.total || 0) - (e.committed || 0))}</div></div>
              <button data-testid={`del-equip-${i}`} onClick={() => delEquip(i)} className="justify-self-end text-ink-faint hover:text-fail-text"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
      </Section>
      <Section icon={Clock} title="Time">
        <div className="grid gap-3 sm:grid-cols-2">{TIME.map(([k, l]) => <Num key={k} group="time" k={k} label={l} />)}</div>
      </Section>
      <p className="mt-4 font-mono text-[11px] text-ink-faint">Every value is labelled by source. BidPilot never invents capacity — assumptions are shown as assumptions.</p>
    </div>
  );
}

function Section({ icon: Icon, title, action, children }) {
  return (
    <div className="mt-6">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2"><Icon className="h-4 w-4 text-navy" /><h2 className="font-serif text-lg font-semibold">{title}</h2></div>
        {action}
      </div>
      {children}
    </div>
  );
}
