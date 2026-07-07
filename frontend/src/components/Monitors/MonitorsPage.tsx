import { useDdMonitors } from "@/api/client";
import { AlertTriangle, CheckCircle2, Ban, Minus } from "lucide-react";

const stateIcon: Record<string, React.ElementType> = {
  OK: CheckCircle2,
  ALERT: AlertTriangle,
  WARN: AlertTriangle,
  "NO DATA": Ban,
  IGNORED: Minus,
  SKIPPED: Minus,
};

const stateColor: Record<string, string> = {
  OK: "bg-emerald-500/20 text-emerald-400",
  ALERT: "bg-red-500/20 text-red-400",
  WARN: "bg-amber-500/20 text-amber-400",
  "NO DATA": "bg-slate-500/20 text-slate-400",
};

export function MonitorsPage() {
  const { data: monitors, isLoading } = useDdMonitors();

  if (isLoading) return <div className="animate-pulse text-slate-500 font-mono text-sm">Loading monitors...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Monitors</h1>
        <p className="text-sm text-slate-500 mt-1 font-mono">Datadog monitors — {monitors?.length ?? 0} total</p>
      </div>

      {!monitors || monitors.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <CheckCircle2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 font-mono text-sm">No monitors configured</p>
          <p className="text-xs text-slate-600 mt-2 font-mono">Create monitors in Datadog → <span className="text-brand-400">https://app.datadoghq.com/monitors/create</span></p>
        </div>
      ) : (
        <div className="space-y-2">
          {monitors.map((m) => {
            const Icon = stateIcon[m.overall_state] ?? Minus;
            const color = stateColor[m.overall_state] ?? "bg-slate-500/20 text-slate-400";
            return (
              <div key={m.id} className="glass rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className={`p-1.5 rounded-lg ${color} shrink-0`}>
                      <Icon className="w-4 h-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">{m.name || m.query}</p>
                      {m.tags && m.tags.length > 0 && (
                        <div className="flex gap-1.5 mt-1 flex-wrap">
                          {m.tags.map((t) => (
                            <span key={t} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-700 text-slate-400">{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-mono font-medium capitalize shrink-0 ${color}`}>
                    {m.overall_state?.toLowerCase()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
