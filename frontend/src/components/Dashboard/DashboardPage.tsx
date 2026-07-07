import { useIncidents, useHealthSummary } from "@/api/client";
import { AlertTriangle, HeartPulse, Activity, CheckCircle2 } from "lucide-react";

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const { data: incidents } = useIncidents();
  const { data: health } = useHealthSummary();

  const activeIncidents = incidents?.filter((i) => i.status === "active") ?? [];
  const healthyServices = health?.filter((h) => h.status === "healthy") ?? [];
  const criticalServices = health?.filter((h) => h.status === "critical") ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-sm text-slate-400 mt-1">
          Real-time observability overview
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={AlertTriangle}
          label="Active Incidents"
          value={activeIncidents.length}
          color="bg-red-500/20 text-red-400"
        />
        <StatCard
          icon={Activity}
          label="Total Incidents"
          value={incidents?.length ?? 0}
          color="bg-amber-500/20 text-amber-400"
        />
        <StatCard
          icon={HeartPulse}
          label="Healthy Services"
          value={healthyServices.length}
          color="bg-emerald-500/20 text-emerald-400"
        />
        <StatCard
          icon={CheckCircle2}
          label="Critical Services"
          value={criticalServices.length}
          color="bg-red-500/20 text-red-400"
        />
      </div>

      {/* Active Incidents */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Active Incidents</h2>
        {activeIncidents.length === 0 ? (
          <div className="flex items-center gap-2 text-slate-400 py-8 justify-center">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span>All clear — no active incidents</span>
          </div>
        ) : (
          <div className="space-y-3">
            {activeIncidents.slice(0, 5).map((inc) => (
              <div
                key={inc.id}
                className="flex items-center justify-between p-3 rounded-lg bg-surface-700/50"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      inc.severity === "SEV-1"
                        ? "bg-red-500/20 text-red-400"
                        : inc.severity === "SEV-2"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-slate-500/20 text-slate-400"
                    }`}
                  >
                    {inc.severity}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-white">{inc.title}</p>
                    {inc.service && (
                      <p className="text-xs text-slate-400">{inc.service}</p>
                    )}
                  </div>
                </div>
                <span className="text-xs text-slate-500">
                  {new Date(inc.started_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Health Summary */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Service Health</h2>
        {!health || health.length === 0 ? (
          <p className="text-slate-400 text-center py-8">
            No health data available
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {health.map((svc) => (
              <div
                key={svc.service}
                className="p-4 rounded-lg bg-surface-700/50"
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-white">{svc.service}</p>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      svc.status === "healthy"
                        ? "bg-emerald-500/20 text-emerald-400"
                        : svc.status === "warning"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-red-500/20 text-red-400"
                    }`}
                  >
                    {svc.status}
                  </span>
                </div>
                <div className="space-y-1">
                  {svc.slis.map((sli) => (
                    <div
                      key={sli.sli_name}
                      className="flex justify-between text-xs"
                    >
                      <span className="text-slate-400">{sli.sli_name}</span>
                      <span className="text-slate-300">
                        {sli.current_value?.toFixed(2) ?? "N/A"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
