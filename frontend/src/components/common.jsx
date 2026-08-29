import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, FileText, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS = {
  PASS: { label: "PASS", cls: "bg-pass-bg text-pass-text border-pass-border", Icon: CheckCircle2 },
  FAIL: { label: "FAIL", cls: "bg-fail-bg text-fail-text border-fail-border", Icon: XCircle },
  NEEDS_REVIEW: { label: "NEEDS REVIEW", cls: "bg-review-bg text-review-text border-review-border", Icon: AlertTriangle },
};

export function StatusBadge({ status, className, testid }) {
  const s = STATUS[status] || STATUS.NEEDS_REVIEW;
  const { Icon } = s;
  return (
    <span data-testid={testid} className={cn("inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide", s.cls, className)}>
      <Icon className="h-3.5 w-3.5" strokeWidth={2} />
      {s.label}
    </span>
  );
}

const SEV = {
  HIGH: "bg-fail-bg text-fail-text border-fail-border",
  MEDIUM: "bg-review-bg text-review-text border-review-border",
  LOW: "bg-secondary text-ink-muted border-line",
};
export function SeverityBadge({ severity, testid }) {
  return (
    <span data-testid={testid} className={cn("inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide", SEV[severity] || SEV.LOW)}>
      {severity === "HIGH" && <AlertTriangle className="h-3.5 w-3.5" />}
      {severity}
    </span>
  );
}

const STAMP = {
  "BID": { cls: "stamp-bid", label: "BID" },
  "BID WITH CONDITIONS": { cls: "stamp-conditional", label: "BID WITH CONDITIONS" },
  "NO-BID": { cls: "stamp-nobid", label: "NO-BID" },
};
export function DecisionStamp({ outcome, size = "lg", testid = "decision-stamp" }) {
  const s = STAMP[outcome] || STAMP["BID WITH CONDITIONS"];
  const sizes = { sm: "text-sm px-3 py-1", md: "text-xl px-4 py-1.5", lg: "text-3xl md:text-4xl", xl: "text-4xl md:text-5xl" };
  return (
    <span data-testid={testid} className={cn("decision-stamp animate-stamp-in", s.cls, sizes[size])}>
      {s.label}
    </span>
  );
}

export function ScoreBar({ label, value, testid }) {
  const color = value >= 75 ? "bg-pass-text" : value >= 50 ? "bg-stamp" : "bg-fail-text";
  return (
    <div data-testid={testid}>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</span>
        <span className="font-mono text-sm font-semibold">{value == null ? "—" : `${value}%`}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-divider overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${value || 0}%` }} />
      </div>
    </div>
  );
}

export function ReadinessRing({ value, testid = "readiness-ring" }) {
  const r = 52, c = 2 * Math.PI * r;
  const off = c - (c * (value || 0)) / 100;
  const color = value >= 75 ? "#1E4620" : value >= 50 ? "#C05621" : "#A50E0E";
  return (
    <div data-testid={testid} className="relative inline-flex items-center justify-center">
      <svg width="132" height="132" className="-rotate-90">
        <circle cx="66" cy="66" r={r} fill="none" stroke="#E5E7EB" strokeWidth="10" />
        <circle cx="66" cy="66" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} style={{ transition: "stroke-dashoffset 0.8s ease" }} />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-serif text-3xl font-bold" style={{ color }}>{value == null ? "—" : `${value}%`}</span>
        <span className="text-[10px] uppercase tracking-widest text-ink-faint">Readiness</span>
      </div>
    </div>
  );
}

export function Confidence({ value }) {
  return <span className="font-mono text-xs text-ink-muted">conf {value ?? "—"}%</span>;
}

export function SourceTag({ doc, page, className }) {
  if (!doc && !page) return <span className="font-mono text-xs text-ink-faint">no source</span>;
  return (
    <span className={cn("inline-flex items-center gap-1 font-mono text-xs text-navy", className)}>
      <FileText className="h-3 w-3" />
      {doc ? <span className="truncate max-w-[160px]">{doc}</span> : null}
      {page ? <span className="text-ink-faint">· p.{page}</span> : null}
    </span>
  );
}

export function Spinner({ className }) {
  return <Loader2 className={cn("animate-spin", className)} />;
}

export function EmptyState({ icon: Icon = FileText, title, description, action, testid = "empty-state" }) {
  return (
    <div data-testid={testid} className="flex flex-col items-center justify-center rounded-md border border-dashed border-line bg-panel/60 px-6 py-16 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-line bg-secondary">
        <Icon className="h-6 w-6 text-navy" strokeWidth={1.5} />
      </div>
      <h3 className="font-serif text-lg font-semibold text-ink">{title}</h3>
      {description && <p className="mt-1 max-w-md text-sm text-ink-muted">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Panel({ title, subtitle, actions, children, className, testid }) {
  return (
    <section data-testid={testid} className={cn("rounded-md border border-line bg-panel shadow-sm", className)}>
      {(title || actions) && (
        <div className="flex items-center justify-between border-b border-divider px-5 py-3">
          <div>
            {title && <h2 className="font-serif text-base font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="text-xs text-ink-muted">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function StatDot({ status }) {
  const color = status === "PASS" ? "bg-pass-text" : status === "FAIL" ? "bg-fail-text" : "bg-review-text";
  return <span className={cn("inline-block h-2 w-2 rounded-full", color)} />;
}

export function PageLoader({ label = "Loading" }) {
  return (
    <div className="flex h-[60vh] flex-col items-center justify-center gap-3 text-ink-muted">
      <Spinner className="h-6 w-6 text-navy" />
      <span className="font-mono text-xs uppercase tracking-widest">{label}</span>
    </div>
  );
}

const SOURCE = {
  VERIFIED: "bg-pass-bg text-pass-text border-pass-border",
  USER_PROVIDED: "bg-navy/10 text-navy border-navy/20",
  AI_EXTRACTED: "bg-secondary text-ink-muted border-line",
  AI_INFERRED: "bg-review-bg text-review-text border-review-border",
  ASSUMPTION: "bg-review-bg text-review-text border-review-border",
  NEEDS_REVIEW: "bg-review-bg text-review-text border-review-border",
};
export function SourceBadge({ source }) {
  if (!source) return null;
  return <span className={cn("inline-block rounded-sm border px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wide", SOURCE[source] || SOURCE.AI_EXTRACTED)}>{source.replace(/_/g, " ")}</span>;
}

export function RiskPill({ risk }) {
  const c = { LOW: "bg-pass-bg text-pass-text border-pass-border", MEDIUM: "bg-review-bg text-review-text border-review-border", HIGH: "bg-fail-bg text-fail-text border-fail-border" };
  return <span className={cn("inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs font-semibold", c[risk] || c.MEDIUM)}>{risk === "HIGH" && <span aria-hidden>▲</span>}{risk}</span>;
}

const BUCKET = {
  PURSUE: "bg-pass-bg text-pass-text border-pass-border",
  WATCH: "bg-review-bg text-review-text border-review-border",
  DEFER: "bg-fail-bg text-fail-text border-fail-border",
};
export function BucketBadge({ bucket, testid }) {
  return <span data-testid={testid} className={cn("inline-block rounded-sm border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide", BUCKET[bucket] || BUCKET.WATCH)}>{bucket}</span>;
}
