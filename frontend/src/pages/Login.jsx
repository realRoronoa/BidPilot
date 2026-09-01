import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Compass, Eye, EyeOff, Loader2, ArrowRight, FileSearch, Building2, ShieldAlert, Stamp } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

const STEPS = [
  { n: "01", t: "Requirements extracted", icon: FileSearch },
  { n: "02", t: "Matched against your company", icon: Building2 },
  { n: "03", t: "Risks & gaps surfaced", icon: ShieldAlert },
  { n: "04", t: "Bid / Conditional / No-Bid", icon: Stamp },
];

export default function Login() {
  const { login, signup } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login"); // login | signup | forgot
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    let res;
    if (mode === "login") res = await login(email, password);
    else if (mode === "signup") res = await signup({ name, email, password, company_name: company });
    else {
      const { api } = await import("@/lib/api");
      try { await api.post("/auth/forgot-password", { email }); toast.success("If that email exists, a reset link was sent."); setMode("login"); }
      catch { toast.error("Could not send reset link."); }
      setLoading(false); return;
    }
    setLoading(false);
    if (res.ok) { toast.success("Welcome to BidPilot"); navigate("/dashboard"); }
    else setError(res.error);
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Left brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden p-12 text-white blueprint-bg lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-stamp"><Compass className="h-6 w-6" /></div>
          <div>
            <div className="font-serif text-2xl font-bold">BidPilot</div>
            <div className="font-mono text-[11px] uppercase tracking-widest text-white/60">Pre-bid intelligence</div>
          </div>
        </div>

        <div className="max-w-lg">
          <h1 className="font-serif text-4xl font-bold leading-tight lg:text-5xl">Should we bid on this tender?</h1>
          <p className="mt-5 text-base leading-relaxed text-white/70">
            Upload the tender and your company evidence. BidPilot compares requirements against your evidence
            and highlights where you stand — before you commit proposal resources.
          </p>
          <div className="mt-9 grid grid-cols-2 gap-4">
            {STEPS.map((s) => (
              <div key={s.n} className="rounded-md border border-white/15 bg-white/5 p-4">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-lg font-semibold text-stamp">{s.n}</span>
                  <s.icon className="h-4 w-4 text-white/70" />
                </div>
                <div className="mt-2 text-sm font-medium text-white/90">{s.t}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="font-mono text-[11px] text-white/40">Decision support for contractors — not legal advice.</div>
      </div>

      {/* Right form panel */}
      <div className="flex items-center justify-center bg-paper px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-stamp text-white"><Compass className="h-5 w-5" /></div>
            <span className="font-serif text-xl font-bold">BidPilot</span>
          </div>

          <h2 className="font-serif text-3xl font-bold text-ink">
            {mode === "login" ? "Welcome back" : mode === "signup" ? "Create your workspace" : "Reset your password"}
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            {mode === "login" ? "Sign in to your workspace" : mode === "signup" ? "Start qualifying tenders in minutes" : "We'll send you a reset link"}
          </p>

          {error && (
            <div data-testid="login-error" className="mt-5 rounded-md border border-fail-border bg-fail-bg px-3 py-2 text-sm text-fail-text">{error}</div>
          )}

          <form onSubmit={submit} className="mt-6 space-y-4">
            {mode === "signup" && (
              <>
                <Field label="Full name"><input data-testid="signup-name" required value={name} onChange={(e) => setName(e.target.value)} className="fld" placeholder="Ravi Menon" /></Field>
                <Field label="Company name (optional)"><input data-testid="signup-company" value={company} onChange={(e) => setCompany(e.target.value)} className="fld" placeholder="ABC Infrastructure Pvt Ltd" /></Field>
              </>
            )}
            <Field label="Work email">
              <input data-testid="login-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="fld" placeholder="you@company.com" />
            </Field>
            {mode !== "forgot" && (
              <Field label="Password">
                <div className="relative">
                  <input data-testid="login-password" type={show ? "text" : "password"} required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} className="fld pr-10" placeholder="••••••••" />
                  <button type="button" data-testid="toggle-password" onClick={() => setShow((s) => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink">
                    {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </Field>
            )}

            {mode === "login" && (
              <div className="flex justify-end">
                <button type="button" data-testid="forgot-link" onClick={() => setMode("forgot")} className="text-sm font-medium text-navy hover:underline">Forgot password?</button>
              </div>
            )}

            <button data-testid="submit-btn" type="submit" disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-navy px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-navy-light disabled:opacity-60">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {mode === "login" ? "Sign In" : mode === "signup" ? "Create workspace" : "Send reset link"}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>



          <p className="mt-6 text-center text-sm text-ink-muted">
            {mode === "login" ? (
              <>New to BidPilot? <button data-testid="goto-signup" onClick={() => { setMode("signup"); setError(""); }} className="font-semibold text-navy hover:underline">Sign Up</button></>
            ) : (
              <>Already have an account? <button data-testid="goto-login" onClick={() => { setMode("login"); setError(""); }} className="font-semibold text-navy hover:underline">Sign In</button></>
            )}
          </p>
        </div>
      </div>

      <style>{`.fld{width:100%;border:1px solid #D1D5DB;border-radius:6px;background:#fff;padding:0.6rem 0.75rem;font-size:0.875rem;outline:none;transition:border-color .15s,box-shadow .15s}.fld:focus{border-color:#1A365D;box-shadow:0 0 0 3px rgba(26,54,93,0.12)}`}</style>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>
      {children}
    </label>
  );
}
