import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  HeartPulse,
  Wrench,
  Search,
  BarChart3,
  Menu,
  X,
  Shield,
} from "lucide-react";
import { useState } from "react";
import { clsx } from "clsx";

const navItems = [
  { to: "/", icon: BarChart3, label: "Dashboard", end: true },
  { to: "/incidents", icon: AlertTriangle, label: "Incidents" },
  { to: "/rca", icon: Search, label: "RCA" },
  { to: "/health", icon: HeartPulse, label: "Health" },
  { to: "/self-healing", icon: Wrench, label: "Self-Healing" },
];

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
        <div className="flex items-center gap-3 px-6 h-16 border-b border-slate-700/50">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">ObservAI</h1>
            <p className="text-xs text-slate-400">Observability Platform</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
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
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-600/20 text-brand-400 border border-brand-500/20"
                    : "text-slate-300 hover:bg-surface-700 hover:text-white"
                )}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700/50">
          <p className="text-xs text-slate-500">
            Powered by Datadog API
          </p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-16 border-b border-slate-700/50 flex items-center px-4 lg:px-6 gap-4 bg-surface-800/50 backdrop-blur-sm">
          <button
            className="lg:hidden p-2 text-slate-300 hover:text-white"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2 text-slate-400">
            <Activity className="w-4 h-4" />
            <span className="text-sm">
              All systems operational
            </span>
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-xs font-bold text-white">
              O
            </div>
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
