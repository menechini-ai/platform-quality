import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  HeartPulse,
  Search,
  BarChart3,
  Menu,
  Monitor,
  FileText,
  LineChart,
  Sigma,
  Bug,
  TestTube,
  Shield,
} from "lucide-react";
import { useState } from "react";
import { clsx } from "clsx";
import { useHealthSummary } from "@/api/client";

const navItems = [
  { to: "/", icon: BarChart3, label: "Dashboard", end: true },
  { to: "/incidents", icon: AlertTriangle, label: "Incidents" },
  { to: "/monitors", icon: Monitor, label: "Monitors" },
  { to: "/logs", icon: FileText, label: "Logs" },
  { to: "/metrics", icon: LineChart, label: "Metrics" },
  { to: "/slos", icon: Sigma, label: "SLOs" },
  { to: "/error-tracking", icon: Bug, label: "Errors" },
  { to: "/synthetics", icon: TestTube, label: "Synthetics" },
  { to: "/rca", icon: Search, label: "RCA" },
  { to: "/health", icon: HeartPulse, label: "Health" },
  { to: "/maturity", icon: Activity, label: "Maturity" },
  { to: "/reports", icon: FileText, label: "Reports" },
  { to: "/self-healing", icon: Activity, label: "Self-Healing" },
];

function VitalSigns() {
  const { data: health } = useHealthSummary();
  const healthy = health?.filter((h) => h.status === "healthy").length ?? 0;
  const total = health?.length ?? 0;
  const critical = health?.filter((h) => h.status === "critical").length ?? 0;
  const now = new Date();
  const utc = now.toUTCString().slice(17, 25);

  return (
    <div className="h-10 bg-surface-800 border-b border-brand-600/20 flex items-center px-4 lg:px-6 gap-5 text-xs font-mono shrink-0 overflow-x-auto">
      {total > 0 && (
        <>
          <span className="flex items-center gap-1.5 text-slate-400 whitespace-nowrap">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            {healthy}/{total} up
          </span>
          {critical > 0 && (
            <span className="flex items-center gap-1.5 text-red-400 whitespace-nowrap">
              <AlertTriangle className="w-3 h-3" />
              {critical} critical
            </span>
          )}
          <span className="text-slate-600">|</span>
        </>
      )}
      <span className="flex items-center gap-1.5 text-slate-500 whitespace-nowrap">
        <Activity className="w-3 h-3" />
        All systems operational
      </span>
      <span className="flex-1" />
      <span className="text-slate-500 tabular-nums whitespace-nowrap">{utc} UTC</span>
    </div>
  );
}

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="flex h-screen bg-surface-900">
      {/* Backdrop for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed lg:static inset-y-0 left-0 z-30 w-64 bg-surface-800 border-r border-slate-700/50 transition-transform duration-200",
          "flex flex-col",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 h-14 border-b border-slate-700/50">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-cyan-800 flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold font-mono text-white">ObservAI</h1>
            <p className="text-[10px] text-slate-500 font-mono">observability</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = item.end
              ? location.pathname === item.to
              : location.pathname.startsWith(item.to);

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setSidebarOpen(false)}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-600/10 text-brand-400 border border-brand-500/20"
                    : "text-slate-400 hover:bg-surface-700 hover:text-slate-200"
                )}
              >
                <item.icon className="w-4.5 h-4.5" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-700/50">
          <p className="text-[10px] text-slate-600 font-mono">
            Datadog API — ObservAI v0.1
          </p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Vital signs bar */}
        <VitalSigns />

        {/* Top bar */}
        <header className="h-12 border-b border-slate-700/50 flex items-center px-4 lg:px-6 gap-4 bg-surface-800/50">
          <button
            className="lg:hidden p-2 text-slate-400 hover:text-white -ml-2"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </button>

          <span className="font-mono text-xs text-slate-500 hidden sm:block">
            {location.pathname === "/" ? "~" : location.pathname}
          </span>

          <div className="flex-1" />

          <div className="w-7 h-7 rounded-full bg-brand-600/20 flex items-center justify-center text-[10px] font-mono font-bold text-brand-400">
            O
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
