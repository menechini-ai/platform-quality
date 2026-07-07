import { useSlos, useHealthSummary } from "@/api/client";
import { HeartPulse, Target, TrendingDown } from "lucide-react";

function SLICard({
  name,
  value,
  target,
}: {
  name: string;
  value?: number;
  target?: number;
}) {
  const ratio = value !== undefined && target ? (value / target) * 100 : 0;
  const isHealthy = ratio >= 100;

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-slate-400">{name}</p>
        <div
          className={`w-2 h-2 rounded-full ${
            isHealthy ? "bg-emerald-400" : "bg-red-400"
          }`}
        />
      </div>
      <p className="text-xl font-bold text-white">
        {value?.toFixed(3) ?? "N/A"}
      </p>
      <div className="mt-2 h-1.5 rounded-full bg-slate-700 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            isHealthy ? "bg-emerald-500" : "bg-red-500"
          }`}
          style={{ width: `${Math.min(ratio, 100)}%` }}
        />
      </div>
      <p className="text-xs text-slate-500 mt-1">
        Target: {target?.toFixed(3) ?? "N/A"}
      </p>
    </div>
  );
}

export function HealthPage() {
  const { data: slos } = useSlos();
  const { data: health } = useHealthSummary();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Product Health</h1>
        <p className="text-sm text-slate-400 mt-1">
          SLO tracking, burn-rate monitoring, and service health
        </p>
      </div>

      {/* Service Health */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <HeartPulse className="w-5 h-5 text-emerald-400" />
          Service Health Overview
        </h2>

        {!health || health.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">
            No health data yet
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {health.map((svc) => (
              <div
                key={svc.service}
                className="p-4 rounded-lg bg-surface-700/50"
              >
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-white">
                    {svc.service}
                  </p>
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

                <div className="space-y-3">
                  {svc.slis.map((sli) => (
                    <div key={sli.sli_name}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-400">{sli.sli_name}</span>
                        <span className="text-slate-300">
                          {sli.current_value?.toFixed(3)}
                        </span>
                      </div>
                      {sli.error_budget_remaining !== undefined && (
                        <div className="flex items-center gap-1 text-xs">
                          <TrendingDown className="w-3 h-3 text-slate-500" />
                          <span className="text-slate-500">
                            Budget:{" "}
                            {(sli.error_budget_remaining * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SLOs */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-brand-400" />
          Service Level Objectives
        </h2>

        {!slos || slos.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">
            No SLOs configured yet
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {slos.map((slo) => (
              <SLICard
                key={slo.id}
                name={slo.name}
                value={undefined}
                target={slo.target}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
