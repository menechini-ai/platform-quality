import { useIncidents, useHealthSummary, useDdMonitors, useDdSlos, useDdMetrics, type DdMetricPoint } from "@/api/client";
import { AlertTriangle, HeartPulse, Activity, CheckCircle2, Monitor, Sigma } from "lucide-react";
import { Sparkline } from "@/components/ui/Sparkline";

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
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className="text-2xl font-bold text-white tabular-nums">{value}</p>
        </div>
      </div>
    </div>
  );
}

function TrendSparklineCard({ title, metric }: { title: string; metric: string }) {
  const { data } = useDdMetrics({ metric, agg: "avg", tags: "*", days: 1 });
  const resp = (data as Record<string, unknown>)?.resp as
    | { series?: { metric: string; points: DdMetricPoint[] }[] }
    | undefined;
  const vals = resp?.series?.[0]?.points?.map((p) => p.value).filter((v) => v != null) ?? [];

  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-white font-mono">{title}</p>
        {vals.length > 0 && (
          <span className="text-xs text-slate-500 font-mono tabular-nums">{vals[vals.length - 1].toFixed(2)}</span>
        )}
      </div>
      {vals.length > 1 ? (
        <Sparkline data={vals} />
      ) : (
        <div className="h-8 flex items-center text-xs text-slate-600 font-mono">No data</div>
      )}
    </div>
  );
}

export function DashboardPage() {
  const { data: incidents } = useIncidents();
  const { data: health } = useHealthSummary();
  const { data: monitors } = useDdMonitors();
  const { data: slos } = useDdSlos();

  const activeIncidents = incidents?.filter((i) => i.status === "active") ?? [];
  const alertMonitors = monitors?.filter((m) => m.overall_state === "ALERT" || m.overall_state === "WARN") ?? [];
  const breachedSlos = slos?.filter((s) => s.overall_status === "breached") ?? [];
  const criticalHealth = health?.filter((h) => h.status === "critical" || h.status === "warning") ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-sm text-slate-400 mt-1 font-mono">Control room overview — {new Date().toISOString().slice(11, 19)} UTC</p>
      </div>

      {/* Stats grid — 6 cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        <StatCard icon={AlertTriangle} label="Active Incidents" value={activeIncidents.length} color="bg-red-500/20 text-red-400" />
        <StatCard icon={Monitor} label="Alerting Monitors" value={alertMonitors.length} color="bg-amber-500/20 text-amber-400" />
        <StatCard icon={Sigma} label="Breached SLOs" value={breachedSlos.length} color="bg-rose-500/20 text-rose-400" />
        <StatCard icon={HeartPulse} label="Healthy Services" value={health?.filter((h) => h.status === "healthy").length ?? 0} color="bg-emerald-500/20 text-emerald-400" />
        <StatCard icon={Activity} label="Total Monitors" value={monitors?.length ?? 0} color="bg-brand-500/20 text-brand-400" />
        <StatCard icon={CheckCircle2} label="Critical Services" value={criticalHealth.length} color="bg-red-500/20 text-red-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alerting Monitors */}
        <div className="glass rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4 font-mono uppercase tracking-wider">Alerting Monitors</h2>
          {alertMonitors.length === 0 ? (
            <div className="flex items-center gap-2 text-slate-500 py-8 justify-center">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="text-sm font-mono">All monitors OK</span>
            </div>
          ) : (
            <div className="space-y-2">
              {alertMonitors.slice(0, 8).map((m) => (
                <div key={m.id} className="flex items-center justify-between p-2.5 rounded-lg bg-surface-700/50">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${m.overall_state === "ALERT" ? "bg-red-400" : "bg-amber-400"}`} />
                    <p className="text-sm text-white truncate">{m.name || m.query}</p>
                  </div>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${m.overall_state === "ALERT" ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"}`}>
                    {m.overall_state}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Breached SLOs */}
        <div className="glass rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4 font-mono uppercase tracking-wider">SLO Status</h2>
          {!slos || slos.length === 0 ? (
            <div className="flex items-center gap-2 text-slate-500 py-8 justify-center">
              <Sigma className="w-5 h-5 text-slate-500" />
              <span className="text-sm font-mono">No SLOs defined</span>
            </div>
          ) : (
            <div className="space-y-3">
              {slos.slice(0, 6).map((slo) => {
                const target = slo.thresholds?.[0]?.target ?? slo.target;
                const pct = (target * 100).toFixed(1);
                const breached = slo.overall_status === "breached";
                return (
                  <div key={slo.id}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-white truncate mr-2">{slo.name}</span>
                      <span className={`font-mono tabular-nums ${breached ? "text-red-400" : "text-emerald-400"}`}>{pct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-surface-700 overflow-hidden">
                      <div className={`h-full rounded-full transition-all ${breached ? "bg-red-400" : "bg-emerald-400"}`} style={{ width: `${Math.min(Number(pct), 100)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Active Incidents */}
        <div className="glass rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4 font-mono uppercase tracking-wider">Active Incidents</h2>
          {activeIncidents.length === 0 ? (
            <div className="flex items-center gap-2 text-slate-500 py-8 justify-center">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="text-sm font-mono">All clear — no active incidents</span>
            </div>
          ) : (
            <div className="space-y-2">
              {activeIncidents.slice(0, 5).map((inc) => (
                <div key={inc.id} className="flex items-center justify-between p-2.5 rounded-lg bg-surface-700/50">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      inc.severity === "SEV-1" ? "bg-red-500/20 text-red-400" :
                      inc.severity === "SEV-2" ? "bg-amber-500/20 text-amber-400" :
                      "bg-slate-500/20 text-slate-400"
                    }`}>{inc.severity}</span>
                    <p className="text-sm text-white truncate">{inc.title}</p>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">{new Date(inc.started_at).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Service Health */}
        <div className="glass rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4 font-mono uppercase tracking-wider">Service Health</h2>
          {!health || health.length === 0 ? (
            <p className="text-sm font-mono text-slate-500 text-center py-8">No health data</p>
          ) : (
            <div className="space-y-2">
              {health.slice(0, 8).map((svc) => (
                <div key={svc.service} className="flex items-center justify-between p-2.5 rounded-lg bg-surface-700/50">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${svc.status === "healthy" ? "bg-emerald-400" : svc.status === "warning" ? "bg-amber-400" : "bg-red-400"}`} />
                    <p className="text-sm text-white">{svc.service}</p>
                  </div>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${svc.status === "healthy" ? "bg-emerald-500/20 text-emerald-400" : svc.status === "warning" ? "bg-amber-500/20 text-amber-400" : "bg-red-500/20 text-red-400"}`}>
                    {svc.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Trends — sparklines */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <TrendSparklineCard title="CPU Trend (24h)" metric="avg:system.cpu.user{*} by {host}.rollup(avg, 3600)" />
        <TrendSparklineCard title="Memory Trend (24h)" metric="avg:system.mem.used{*} by {host}.rollup(avg, 3600)" />
      </div>
    </div>
  );
}
