import React, { useEffect, useState } from "react";
import { CreditCard, Check, Loader2, TriangleAlert, Download, CheckCircle, ArrowRight, X } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { PageLoader } from "@/components/common";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

// ---- Usage meter bar ----
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

// ---- Payment success modal ----
function PaymentSuccessModal({ planName, planPrice, features, expiryDate, onClose }) {
  const navigate = useNavigate();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative mx-4 w-full max-w-md rounded-xl border border-line bg-panel p-8 shadow-2xl">
        <button onClick={onClose} className="absolute right-4 top-4 text-ink-faint hover:text-ink">
          <X className="h-5 w-5" />
        </button>
        <div className="flex flex-col items-center text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-pass-bg">
            <CheckCircle className="h-8 w-8 text-pass-text" />
          </div>
          <h2 className="mt-4 font-serif text-2xl font-bold">Payment Successful</h2>
          <p className="mt-1 text-sm text-ink-muted">
            <span className="font-semibold text-ink">{planName} Plan</span> activated
          </p>
          {planPrice != null && planPrice > 0 && (
            <p className="mt-0.5 font-mono text-sm font-semibold text-ink">
              ₹{planPrice.toLocaleString("en-IN")}/month
            </p>
          )}
          {expiryDate && (
            <p className="mt-1 font-mono text-[11px] text-ink-faint">
              Plan active until {fmtDate(expiryDate)}
            </p>
          )}
          <div className="mt-6 w-full rounded-md border border-line bg-paper/40 p-4 text-left">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-wide text-ink-faint">You now have</p>
            <ul className="space-y-1.5">
              {(features || []).map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-ink-muted">
                  <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-pass-text" /> {f}
                </li>
              ))}
            </ul>
          </div>
          <div className="mt-6 flex w-full flex-col gap-3">
            <button
              onClick={() => { onClose(); navigate("/analyses/new"); }}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-navy px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-light"
            >
              Start Analyzing a Tender <ArrowRight className="h-4 w-4" />
            </button>
            <button onClick={onClose} className="text-sm text-ink-muted hover:text-ink">
              Back to Billing
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Billing() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(null);
  const [successInfo, setSuccessInfo] = useState(null); // {planName, features, expiryDate}

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
            // Reload billing data first, then show success modal
            await load();
            setSuccessInfo({
              planName: v.plan_name,
              planPrice: (plans || []).find((p) => p.id === planId)?.price,
              features: v.plan_features || [],
              expiryDate: v.billing_period_end,
            });
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

  // Derive plan status display
  const isActive = sub?.status === "active";
  const statusLabel = isActive ? "ACTIVE" : (sub?.status || "—");
  const statusCls = isActive
    ? "bg-pass-bg text-pass-text"
    : "bg-divider text-ink-faint";

  return (
    <>
      {successInfo && (
        <PaymentSuccessModal
          planName={successInfo.planName}
          planPrice={successInfo.planPrice}
          features={successInfo.features}
          expiryDate={successInfo.expiryDate}
          onClose={() => setSuccessInfo(null)}
        />
      )}

      <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
        <div className="flex items-center justify-between">
          <div><h1 className="font-serif text-2xl font-bold">Billing</h1><p className="mt-1 text-sm text-ink-muted">Manage your subscription, usage and invoices.</p></div>
          <span className="rounded-sm border border-review-border bg-review-bg px-3 py-1 font-mono text-[11px] font-semibold uppercase text-review-text">Razorpay Test Mode — no real charge</span>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          {/* Current Plan Card */}
          <div className="rounded-md border border-line bg-panel p-5 shadow-sm">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wide text-ink-faint"><CreditCard className="h-3.5 w-3.5" /> Current plan</div>
            <div className="mt-2 font-serif text-2xl font-bold">{sub?.plan_name || "—"}</div>
            {sub?.plan_price != null && (
              <div className="mt-0.5 text-sm text-ink-muted">
                {sub.plan_price === 0 ? "Free" : `₹${sub.plan_price.toLocaleString("en-IN")}`}/month
              </div>
            )}
            <div className="mt-3 flex items-center gap-2">
              <span className={`rounded-sm px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${statusCls}`}>
                {statusLabel}
              </span>
            </div>
            <div className="mt-3 space-y-1 text-sm text-ink-muted">
              {sub?.billing_cycle && sub?.plan_id !== "plan-free" && (
                <div>Billing cycle: {sub.billing_cycle}</div>
              )}
              {sub?.plan_id === "plan-free"
                ? <div className="font-mono text-[11px] text-ink-faint">Free plan — no expiry</div>
                : sub?.billing_period_end
                  ? <div>Plan active until: {fmtDate(sub.billing_period_end)}</div>
                  : null}
            </div>
          </div>

          {/* Usage This Cycle */}
          <div className="rounded-md border border-line bg-panel p-5 shadow-sm lg:col-span-2">
            <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Usage this cycle</div>
            <div className="mt-3 grid gap-4 sm:grid-cols-3">
              {usage ? (
                <>
                  <Meter label="Analyses" used={usage.analyses_used ?? 0} limit={usage.analyses_limit ?? 5} />
                  <Meter label="Storage" used={usage.storage_used_gb ?? 0} limit={usage.storage_limit_gb ?? 5} unit=" GB" />
                  <Meter label="Users" used={usage.users_used ?? 1} limit={usage.users_limit ?? 2} />
                </>
              ) : (
                <p className="col-span-3 text-sm text-ink-faint">Usage data not available.</p>
              )}
            </div>
          </div>
        </div>

        {/* Upgrade prompt for Free users at limit */}
        {sub?.plan_id === "plan-free" && usage && usage.analyses_used >= usage.analyses_limit && (
          <div className="mt-6 rounded-md border border-review-border bg-review-bg p-4">
            <p className="font-semibold text-ink">
              You've used all {usage.analyses_limit} free {usage.analyses_limit === 1 ? "analysis" : "analyses"} this month.
            </p>
            <p className="mt-1 text-sm text-ink-muted">Upgrade to continue analyzing tenders.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button onClick={() => upgrade("plan-starter")} disabled={!!busy}
                className="rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white hover:bg-navy-light disabled:opacity-60">
                {busy === "plan-starter" ? <Loader2 className="mx-auto h-4 w-4 animate-spin" /> : "Upgrade to Starter — ₹3,999/mo"}
              </button>
              <button onClick={() => upgrade("plan-pro")} disabled={!!busy}
                className="rounded-md border border-navy px-4 py-2 text-sm font-semibold text-navy hover:bg-navy/5 disabled:opacity-60">
                {busy === "plan-pro" ? <Loader2 className="mx-auto h-4 w-4 animate-spin" /> : "Upgrade to Professional — ₹14,999/mo"}
              </button>
            </div>
          </div>
        )}

        {/* Plans */}
        <h2 className="mt-8 font-serif text-xl font-semibold">Plans</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {(plans || []).map((p) => {
            const current = sub?.plan_id === p.id;
            const isFree = p.is_free || p.price === 0;
            const priceDisplay = isFree ? "Free" : `₹${p.price.toLocaleString("en-IN")}`;
            return (
              <div key={p.id} data-testid={`plan-${p.id}`} className={`rounded-md border bg-panel p-5 shadow-sm ${current ? "border-navy ring-2 ring-navy/20" : "border-line"}`}>
                <div className="flex items-center justify-between"><h3 className="font-serif text-lg font-bold">{p.name}</h3>{current && <span className="rounded-sm bg-navy px-2 py-0.5 text-[10px] font-semibold text-white">CURRENT</span>}</div>
                <div className="mt-2"><span className="font-serif text-3xl font-bold">{priceDisplay}</span><span className="text-sm text-ink-muted">/{p.period}</span></div>
                <ul className="mt-4 space-y-1.5 text-sm text-ink-muted">{p.features.map((f) => <li key={f} className="flex items-start gap-2"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-pass-text" /> {f}</li>)}</ul>
                <button
                  data-testid={`select-plan-${p.id}`}
                  disabled={current || !!busy || isFree}
                  onClick={() => !isFree && upgrade(p.id)}
                  className={`mt-5 w-full rounded-md px-4 py-2 text-sm font-semibold ${
                    current
                      ? "cursor-default border border-line text-ink-faint"
                      : isFree
                        ? "cursor-default border border-line text-ink-faint"
                        : "bg-navy text-white hover:bg-navy-light"
                  } disabled:opacity-60`}
                >
                  {busy === p.id
                    ? <Loader2 className="mx-auto h-4 w-4 animate-spin" />
                    : current
                      ? "Current plan"
                      : isFree
                        ? "Free — no payment needed"
                        : "Upgrade with Razorpay"}
                </button>
              </div>
            );
          })}
        </div>

        {/* Payment method + Invoices */}
        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          <div className="rounded-md border border-line bg-panel p-5 shadow-sm">
            <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint">Payment method</div>
            {sub?.payment_method?.last4 ? (
              <div className="mt-3 flex items-center gap-3 rounded-md border border-divider bg-paper/40 p-3">
                <CreditCard className="h-6 w-6 text-navy" />
                <div>
                  <div className="text-sm font-medium">{sub.payment_method.brand} •••• {sub.payment_method.last4}</div>
                  <div className="font-mono text-xs text-ink-muted">exp {sub.payment_method.exp}</div>
                </div>
              </div>
            ) : (
              <div className="mt-3 flex items-center gap-3 rounded-md border border-divider bg-paper/40 p-3">
                <CreditCard className="h-6 w-6 text-ink-faint" />
                <div className="text-sm text-ink-muted">Managed via Razorpay</div>
              </div>
            )}
            <p className="mt-2 font-mono text-[11px] text-ink-faint">Test mode — no real payment method stored.</p>
          </div>

          {/* Billing History */}
          <div className="rounded-md border border-line bg-panel shadow-sm lg:col-span-2">
            <div className="border-b border-divider px-5 py-3"><h3 className="font-serif text-base font-semibold">Invoices &amp; billing history</h3></div>
            {invoices && invoices.length > 0 ? (
              <table className="w-full text-sm">
                <thead><tr className="border-b border-divider text-left font-mono text-[11px] uppercase text-ink-faint"><th className="px-5 py-2.5">Invoice</th><th className="px-3 py-2.5">Period</th><th className="px-3 py-2.5">Date</th><th className="px-3 py-2.5">Amount</th><th className="px-3 py-2.5">Status</th><th className="px-5 py-2.5" /></tr></thead>
                <tbody>{invoices.map((inv) => (
                  <tr key={inv.id} className="border-b border-divider last:border-0">
                    <td className="px-5 py-3 font-mono text-xs">{inv.number}</td>
                    <td className="px-3 py-3">{inv.period}</td>
                    <td className="px-3 py-3 font-mono text-xs text-ink-muted">{fmtDate(inv.date)}</td>
                    <td className="px-3 py-3 font-mono">₹{typeof inv.amount === "number" ? inv.amount.toLocaleString("en-IN") : inv.amount}</td>
                    <td className="px-3 py-3">
                      <span className={`rounded-sm px-2 py-0.5 text-xs font-semibold ${inv.status === "Paid" || inv.status === "paid" ? "bg-pass-bg text-pass-text" : "bg-stamp-bg text-stamp-text"}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button className="text-ink-faint hover:text-navy" onClick={() => toast.info("Invoice PDF not available in test mode.")}>
                        <Download className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            ) : (
              <div className="px-5 py-10 text-center text-sm text-ink-faint">
                No payment records yet. Complete a Razorpay test payment to see billing history.
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
