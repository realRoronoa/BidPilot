import React, { useEffect, useState } from "react";
import { CreditCard, Check, Loader2, TriangleAlert, Download } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { PageLoader } from "@/components/common";
import { toast } from "sonner";

function Meter({ label, used, limit, unit = "" }) {
  const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const near = pct >= 80;
  return (
    <div>
      <div className="flex items-baseline justify-between text-sm"><span className="font-medium">{label}</span><span className="font-mono text-xs text-ink-muted">{used}{unit} / {limit}{unit}</span></div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-divider"><div className={`h-full rounded-full ${near ? "bg-stamp" : "bg-navy"}`} style={{ width: `${pct}%` }} /></div>
      {near && <div className="mt-1 flex items-center gap-1 font-mono text-[11px] text-stamp"><TriangleAlert className="h-3 w-3" /> Approaching limit</div>}
    </div>
  );
}

export default function Billing() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(null);
  const load = () => api.get("/billing").then(setData).catch(() => setData(false));
  useEffect(() => { load(); }, []);
  if (data === null) return <PageLoader label="Loading billing" />;
  if (!data) return <div className="p-8">Failed to load billing.</div>;
  const { subscription: sub, usage, plans, invoices } = data;

  const loadRazorpay = () => new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });

  const upgrade = async (planId) => {
    setBusy(planId);
    try {
      const order = await api.post("/billing/razorpay/order", { plan_id: planId });
      const ok = await loadRazorpay();
      if (!ok) { toast.error("Could not load Razorpay Checkout"); setBusy(null); return; }
      const rzp = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "BidPilot",
        description: `${order.plan_name} plan (Test Mode)`,
        order_id: order.order_id,
        prefill: { name: order.customer_name, email: order.customer_email },
        theme: { color: "#1A365D" },
        handler: async (resp) => {
          try {
            const v = await api.post("/billing/razorpay/verify", {
              plan_id: planId,
              razorpay_order_id: resp.razorpay_order_id,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature: resp.razorpay_signature,
            });
            toast.success(v.message || "Payment verified");
            load();
          } catch (e) {
            toast.error(e.response?.data?.detail || "Payment verification failed. Your plan was not changed.");
          }
          setBusy(null);
        },
        modal: { ondismiss: () => { toast.info("Payment cancelled — no changes made."); setBusy(null); } },
      });
      rzp.on("payment.failed", (r) => { toast.error(r.error?.description || "Payment failed."); setBusy(null); });
      rzp.open();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not start payment.");
      setBusy(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
      <div className="flex items-center justify-between">
        <div><h1 className="font-serif text-2xl font-bold">Billing</h1><p className="mt-1 text-sm text-ink-muted">Manage your subscription, usage and invoices.</p></div>
        <span className="rounded-sm border border-review-border bg-review-bg px-3 py-1 font-mono text-[11px] font-semibold uppercase text-review-text">Razorpay Test Mode — no real charge</span>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="rounded-md border border-line bg-panel p-5 shadow-sm">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wide text-ink-faint"><CreditCard className="h-3.5 w-3.5" /> Current plan</div>
          <div className="mt-2 font-serif text-2xl font-bold">{sub?.plan_name}</div>
          <div className="mt-1 text-sm text-ink-muted">Billing cycle: {sub?.billing_cycle}</div>
          <div className="text-sm text-ink-muted">Next billing: {fmtDate(sub?.next_billing_date)}</div>
        </div>
        <div className="rounded-md border border-line bg-panel p-5 shadow-sm lg:col-span-2">
          <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Usage this cycle</div>
          <div className="mt-3 grid gap-4 sm:grid-cols-3">
            {usage && <>
              <Meter label="Analyses" used={usage.analyses_used} limit={usage.analyses_limit} />
              <Meter label="Storage" used={usage.storage_used_gb} limit={usage.storage_limit_gb} unit=" GB" />
              <Meter label="Users" used={usage.users_used} limit={usage.users_limit} />
            </>}
          </div>
        </div>
      </div>

      {/* Plans */}
      <h2 className="mt-8 font-serif text-xl font-semibold">Plans</h2>
      <div className="mt-3 grid gap-4 md:grid-cols-3">
        {plans.map((p) => {
          const current = sub?.plan_id === p.id;
          return (
            <div key={p.id} data-testid={`plan-${p.id}`} className={`rounded-md border bg-panel p-5 shadow-sm ${current ? "border-navy ring-2 ring-navy/20" : "border-line"}`}>
              <div className="flex items-center justify-between"><h3 className="font-serif text-lg font-bold">{p.name}</h3>{current && <span className="rounded-sm bg-navy px-2 py-0.5 text-[10px] font-semibold text-white">CURRENT</span>}</div>
              <div className="mt-2"><span className="font-serif text-3xl font-bold">${p.price}</span><span className="text-sm text-ink-muted">/{p.period}</span></div>
              <ul className="mt-4 space-y-1.5 text-sm text-ink-muted">{p.features.map((f) => <li key={f} className="flex items-start gap-2"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-pass-text" /> {f}</li>)}</ul>
              <button data-testid={`select-plan-${p.id}`} disabled={current || busy} onClick={() => upgrade(p.id)} className={`mt-5 w-full rounded-md px-4 py-2 text-sm font-semibold ${current ? "cursor-default border border-line text-ink-faint" : "bg-navy text-white hover:bg-navy-light"} disabled:opacity-60`}>
                {busy === p.id ? <Loader2 className="mx-auto h-4 w-4 animate-spin" /> : current ? "Current plan" : "Upgrade with Razorpay"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Payment + invoices */}
      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="rounded-md border border-line bg-panel p-5 shadow-sm">
          <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Payment method</div>
          <div className="mt-3 flex items-center gap-3 rounded-md border border-divider bg-paper/40 p-3">
            <CreditCard className="h-6 w-6 text-navy" />
            <div><div className="text-sm font-medium">{sub?.payment_method?.brand} •••• {sub?.payment_method?.last4}</div><div className="font-mono text-xs text-ink-muted">exp {sub?.payment_method?.exp}</div></div>
          </div>
          <p className="mt-2 font-mono text-[11px] text-ink-faint">Demo card. Connect a real provider to enable live billing.</p>
        </div>
        <div className="rounded-md border border-line bg-panel shadow-sm lg:col-span-2">
          <div className="border-b border-divider px-5 py-3"><h3 className="font-serif text-base font-semibold">Invoices & billing history</h3></div>
          <table className="w-full text-sm">
            <thead><tr className="border-b border-divider text-left font-mono text-[11px] uppercase text-ink-faint"><th className="px-5 py-2.5">Invoice</th><th className="px-3 py-2.5">Period</th><th className="px-3 py-2.5">Date</th><th className="px-3 py-2.5">Amount</th><th className="px-3 py-2.5">Status</th><th className="px-5 py-2.5" /></tr></thead>
            <tbody>{invoices.map((inv) => (
              <tr key={inv.id} className="border-b border-divider last:border-0">
                <td className="px-5 py-3 font-mono text-xs">{inv.number}</td>
                <td className="px-3 py-3">{inv.period}</td>
                <td className="px-3 py-3 font-mono text-xs text-ink-muted">{fmtDate(inv.date)}</td>
                <td className="px-3 py-3 font-mono">${inv.amount}</td>
                <td className="px-3 py-3"><span className="rounded-sm bg-pass-bg px-2 py-0.5 text-xs font-semibold text-pass-text">{inv.status}</span></td>
                <td className="px-5 py-3 text-right"><button className="text-ink-faint hover:text-navy" onClick={() => toast.info("Demo invoice — download not available in sandbox.")}><Download className="h-4 w-4" /></button></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
