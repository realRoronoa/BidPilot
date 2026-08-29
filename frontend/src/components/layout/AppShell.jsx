import React, { useState, useEffect } from "react";
import { NavLink, useNavigate, Link } from "react-router-dom";
import {
  LayoutDashboard, FileSearch, Building2, FolderOpen, Bell, Settings,
  Users, CreditCard, Plus, Menu, X, LogOut, Compass, Search, ShieldCheck,
  Layers, Briefcase, Gauge,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/portfolio", label: "Portfolio", icon: Layers },
  { to: "/opportunities", label: "Opportunities", icon: Briefcase },
  { to: "/analyses", label: "Analyses", icon: FileSearch },
  { to: "/company", label: "Company", icon: Building2 },
  { to: "/documents", label: "Documents", icon: FolderOpen },
  { to: "/notifications", label: "Notifications", icon: Bell },
];
const ADMIN_NAV = [
  { to: "/capacity", label: "Capacity", icon: Gauge },
  { to: "/users", label: "Users & Roles", icon: Users },
  { to: "/billing", label: "Billing", icon: CreditCard },
  { to: "/settings", label: "Settings", icon: Settings },
];

function NavItem({ item, onClick }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      onClick={onClick}
      data-testid={`nav-${item.label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`}
      className={({ isActive }) => cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        isActive ? "bg-navy-light text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
      )}
    >
      <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
      {item.label}
    </NavLink>
  );
}

function Sidebar({ onNavigate, unread }) {
  return (
    <div className="flex h-full flex-col blueprint-bg">
      <Link to="/dashboard" onClick={onNavigate} className="flex items-center gap-2.5 border-b border-white/10 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-stamp text-white">
          <Compass className="h-5 w-5" />
        </div>
        <div>
          <div className="font-serif text-lg font-bold leading-none text-white">BidPilot</div>
          <div className="mt-0.5 font-mono text-[10px] uppercase tracking-widest text-white/50">Know before you bid</div>
        </div>
      </Link>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        <Link to="/analyses/new" onClick={onNavigate} data-testid="sidebar-new-analysis"
          className="mb-3 flex items-center justify-center gap-2 rounded-md bg-stamp px-3 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-stamp-dark">
          <Plus className="h-4 w-4" /> New Analysis
        </Link>
        {NAV.map((i) => (
          <div key={i.to} className="relative">
            <NavItem item={i} onClick={onNavigate} />
            {i.label === "Notifications" && unread > 0 && (
              <span className="absolute right-3 top-2.5 rounded-full bg-stamp px-1.5 text-[10px] font-bold text-white">{unread}</span>
            )}
          </div>
        ))}
        <div className="px-3 pb-1 pt-4 font-mono text-[10px] uppercase tracking-widest text-white/40">Workspace</div>
        {ADMIN_NAV.map((i) => <NavItem key={i.to} item={i} onClick={onNavigate} />)}
      </nav>
      <div className="border-t border-white/10 px-5 py-3">
        <div className="flex items-center gap-2 font-mono text-[11px] text-white/50">
          <ShieldCheck className="h-3.5 w-3.5" /> Decision support · not legal advice
        </div>
      </div>
    </div>
  );
}

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [drawer, setDrawer] = useState(false);
  const [unread, setUnread] = useState(0);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    api.get("/notifications").then((n) => setUnread(n.filter((x) => !x.read).length)).catch(() => {});
  }, []);

  const doLogout = async () => { await logout(); navigate("/login"); };

  return (
    <div className="flex h-screen overflow-hidden bg-paper">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 lg:block">
        <Sidebar unread={unread} />
      </aside>

      {/* Mobile drawer */}
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setDrawer(false)} />
          <div className="absolute left-0 top-0 h-full w-64">
            <Sidebar unread={unread} onNavigate={() => setDrawer(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-panel px-4">
          <button data-testid="mobile-menu-btn" className="lg:hidden" onClick={() => setDrawer(true)}>
            <Menu className="h-5 w-5 text-navy" />
          </button>
          <div className="hidden items-center gap-2 rounded-md border border-line bg-secondary/60 px-3 py-1.5 sm:flex">
            <Search className="h-4 w-4 text-ink-faint" />
            <input data-testid="global-search" placeholder="Search analyses, tenders, documents…"
              className="w-64 bg-transparent text-sm outline-none placeholder:text-ink-faint" />
          </div>
          <div className="ml-auto flex items-center gap-3">
            <Link to="/notifications" data-testid="topbar-notifications" className="relative rounded-md p-2 hover:bg-secondary">
              <Bell className="h-5 w-5 text-navy" />
              {unread > 0 && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-stamp" />}
            </Link>
            <div className="relative">
              <button data-testid="user-menu-btn" onClick={() => setMenu((m) => !m)} className="flex items-center gap-2 rounded-md py-1 pl-1 pr-2 hover:bg-secondary">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-navy font-mono text-xs font-semibold text-white">
                  {user?.avatar_initials || "U"}
                </span>
                <span className="hidden text-sm font-medium sm:block">{user?.name}</span>
              </button>
              {menu && (
                <div className="absolute right-0 top-11 z-50 w-52 rounded-md border border-line bg-panel p-1 shadow-lg" onMouseLeave={() => setMenu(false)}>
                  <div className="border-b border-divider px-3 py-2">
                    <div className="text-sm font-medium">{user?.name}</div>
                    <div className="font-mono text-xs text-ink-muted">{user?.email}</div>
                    <div className="mt-1 inline-block rounded-sm bg-secondary px-1.5 py-0.5 font-mono text-[10px] uppercase">{user?.role}</div>
                  </div>
                  <Link to="/settings" onClick={() => setMenu(false)} className="block rounded-sm px-3 py-2 text-sm hover:bg-secondary">Settings</Link>
                  <button data-testid="logout-btn" onClick={doLogout} className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-left text-sm text-fail-text hover:bg-fail-bg">
                    <LogOut className="h-4 w-4" /> Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto scrollbar-thin">{children}</main>
      </div>
    </div>
  );
}
