import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useHealthCatalog,
  useHealthStats,
  useKnowledgeBase,
  useHealthForecast,
} from "@/api/client";
import {
  HeartPulse,
  AlertTriangle,
  FileText,
  BookOpen,
  Activity,
  Server,
  GitBranch,
  Search,
  BarChart3,
  Target,
  CalendarDays,
  TrendingUp,
  Clock,
} from "lucide-react";
import { clsx } from "clsx";

const PERIODS = [
  { label: "1d", days: 1 },
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
] as const;

const PATTERN_COLORS: Record<string, string> = {
  deploy: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  resource: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  latency: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  dependency: "bg-red-500/20 text-red-400 border-red-500/30",
  data_corruption: "bg-orange-500/20 text-orange-400 border-orange-500/30",
};

const SERVICES = ["api-gateway", "user-service", "payment-service", "order-service", "redis"];

function StatCard({
  label,
  value,
  icon: Icon,
  color = "brand-400",
}: {
  label: string;
  value: number | string;
  icon: typeof Server;
  color?: string;
}) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-${color}/20`}>
          <Icon className={`w-5 h-5 text-${color}`} />
        </div>
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-xs text-slate-400">{label}</p>
        </div>
      </div>
    </div>
  );
}

export function HealthPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState<number | undefined>(undefined);
  const { data: catalog, isLoading: catLoading } = useHealthCatalog(days);
  const { data: stats, isLoading: statsLoading } = useHealthStats(days);
  const { data: kb } = useKnowledgeBase();
  const { data: forecast } = useHealthForecast(30);

  // Build service → failure pattern stats
  const servicePatternCount = useMemo(() => {
    if (!catalog) return {};
    const acc: Record<string, Record<string, number>> = {};
    for (const item of catalog) {
      if (item.type !== "incident") continue;
      const svc = item.service || "unknown";
      const pat = item.failure_pattern || "unknown";
      if (!acc[svc]) acc[svc] = {};
      acc[svc][pat] = (acc[svc][pat] || 0) + 1;
    }
    return acc;
  }, [catalog]);

  // Categorize incidents by failure pattern
  const patternIncidents = useMemo(() => {
    if (!catalog) return {};
    const acc: Record<string, any[]> = {};
    for (const item of catalog) {
      if (item.type !== "incident") continue;
      const pat = item.failure_pattern || "uncategorized";
      if (!acc[pat]) acc[pat] = [];
      acc[pat].push(item);
    }
    return acc;
  }, [catalog]);

  const isLoading = catLoading || statsLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <HeartPulse className="w-6 h-6 text-emerald-400" />
          Product Health
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Unified observability catalog — every resource tagged, linked, and traceable
        </p>
      </div>

      {/* Period Selector */}
      <div className="flex items-center gap-2">
        <CalendarDays className="w-4 h-4 text-slate-400" />
        {PERIODS.map((p) => (
          <button
            key={p.label}
            onClick={() => setDays(days === p.days ? undefined : p.days)}
            className={clsx(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              days === p.days
                ? "bg-brand-500/20 text-brand-400 border border-brand-500/40"
                : "bg-surface-700/50 text-slate-400 border border-transparent hover:bg-surface-700 hover:text-slate-300"
            )}
          >
            {p.label}
          </button>
        ))}
        {days && (
          <button
            onClick={() => setDays(undefined)}
            className="text-xs text-slate-500 hover:text-slate-300 ml-1"
          >
            Clear
          </button>
        )}
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <StatCard
            label="Active Incidents"
            value={stats.active_incidents}
            icon={AlertTriangle}
            color="red-400"
          />
          <StatCard
            label="Total Incidents"
            value={stats.total_incidents}
            icon={BarChart3}
            color="brand-400"
          />
          <StatCard
            label="No RCA"
            value={stats.incidents_without_rca}
            icon={Search}
            color="amber-400"
          />
          <StatCard
            label="Runbooks"
            value={stats.total_runbooks}
            icon={BookOpen}
            color="emerald-400"
          />
          <StatCard
            label="Postmortems"
            value={Object.values(stats.reports_by_type).reduce((a, b) => a + b, 0)}
            icon={FileText}
            color="purple-400"
          />
          <StatCard label="SLOs" value={stats.total_slos} icon={Target} color="cyan-400" />
        </div>
      )}

      {/* Incidents by Service + Failure Pattern — Topological Map */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Server className="w-5 h-5 text-brand-400" />
          Service Topology &mdash; Incidents by Failure Pattern
        </h2>

        {isLoading ? (
          <div className="animate-pulse text-slate-400 text-sm py-8 text-center">Loading...</div>
        ) : !catalog || catalog.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">No data yet</p>
        ) : (
          <div className="space-y-4">
            {SERVICES.map((svc) => {
              const patterns = servicePatternCount[svc];
              const total = patterns ? Object.values(patterns).reduce((a, b) => a + b, 0) : 0;
              return (
                <div key={svc} className="bg-surface-700/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Server className="w-4 h-4 text-slate-400" />
                      <span className="font-medium text-white text-sm">{svc}</span>
                    </div>
                    <span className="text-xs text-slate-500">{total} incidents</span>
                  </div>
                  {patterns ? (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(patterns).map(([pat, count]) => (
                        <button
                          key={pat}
                          onClick={() => navigate(`/incidents?service=${svc}&failure_pattern=${pat}`)}
                          className={clsx(
                            "px-2.5 py-1 rounded-full text-xs font-medium border transition-colors",
                            PATTERN_COLORS[pat] || "bg-slate-500/20 text-slate-400 border-slate-500/30",
                            "hover:opacity-80 cursor-pointer"
                          )}
                        >
                          {count}x {pat.replace("_", " ")}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No incidents</p>
                  )}

                  {/* Show incidents for this service */}
                  <div className="mt-3 space-y-1.5">
                    {catalog
                      .filter((i) => i.type === "incident" && i.service === svc)
                      .slice(0, 3)
                      .map((inc) => (
                        <button
                          key={inc.id}
                          onClick={() => navigate(`/incidents/${inc.id}`)}
                          className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors w-full text-left py-0.5"
                        >
                          <span
                            className={clsx(
                              "shrink-0 w-1.5 h-1.5 rounded-full",
                              inc.severity === "SEV-1"
                                ? "bg-red-400"
                                : inc.severity === "SEV-2"
                                  ? "bg-amber-400"
                                  : "bg-slate-500"
                            )}
                          />
                          <span className="truncate">{inc.name}</span>
                        </button>
                      ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Failure Pattern Breakdown */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-brand-400" />
          Failure Pattern Breakdown
        </h2>

        {isLoading ? (
          <div className="animate-pulse text-slate-400 text-sm py-8 text-center">Loading...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(patternIncidents).map(([pattern, incidents]) => {
              const count = incidents.length;
              const sev1 = incidents.filter((i) => i.severity === "SEV-1").length;
              const open = incidents.filter((i) => i.status === "active").length;
              return (
                <div
                  key={pattern}
                  className={clsx(
                    "rounded-lg p-4 border",
                    PATTERN_COLORS[pattern]?.replace("text-", "border-") || "border-slate-600/30",
                    "bg-surface-700/50"
                  )}
                >
                  <p className="text-xs uppercase tracking-wider text-slate-400 mb-1">
                    {pattern.replace("_", " ")}
                  </p>
                  <p className="text-2xl font-bold text-white">{count}</p>
                  <div className="flex gap-3 mt-1 text-xs text-slate-500">
                    <span className="text-red-400">{sev1} SEV-1</span>
                    <span className="text-amber-400">{open} active</span>
                  </div>

                  {/* Linked KB pattern */}
                  {kb &&
                    kb
                      .filter((k) => k.tags?.some((t) => t.includes(pattern)))
                      .slice(0, 1)
                      .map((entry) => (
                        <div key={entry.id} className="mt-3 pt-3 border-t border-slate-600/30">
                          <p className="text-xs text-slate-500 mb-1">Root Cause Pattern</p>
                          <p className="text-xs text-slate-300 line-clamp-2">{entry.root_cause}</p>
                        </div>
                      ))}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Forecast & Risk */}
      {forecast && forecast.risk.length > 0 && (
        <div className="glass rounded-xl p-5">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-brand-400" />
            Forecast &amp; Risk ({forecast.window_days}d window)
          </h2>

          {/* Risk cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
            {forecast.risk.map((r) => (
              <div
                key={r.service}
                className={clsx(
                  "rounded-lg p-4 border",
                  r.level === "high"
                    ? "bg-red-500/10 border-red-500/30"
                    : r.level === "medium"
                      ? "bg-amber-500/10 border-amber-500/30"
                      : "bg-emerald-500/10 border-emerald-500/30"
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-white text-sm">{r.service}</span>
                  <span
                    className={clsx(
                      "px-2 py-0.5 rounded-full text-xs font-medium uppercase",
                      r.level === "high"
                        ? "bg-red-500/20 text-red-400"
                        : r.level === "medium"
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-emerald-500/20 text-emerald-400"
                    )}
                  >
                    {r.level} risk
                  </span>
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  {r.reasons.map((reason, i) => (
                    <p key={i} className="flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 shrink-0" />
                      {reason}
                    </p>
                  ))}
                  {r.mtbf_hours && (
                    <p className="flex items-center gap-1 mt-1 text-slate-500">
                      <Clock className="w-3 h-3" />
                      MTBF {r.mtbf_hours.toFixed(1)}h
                    </p>
                  )}
                  {r.next_incident_estimate && (
                    <p className="text-slate-500 mt-1">
                      Next ~{new Date(r.next_incident_estimate).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* SLO burn-rate table */}
          {forecast.slo_burn.filter((b) => b.burn_rate).length > 0 && (
            <div>
              <p className="text-sm font-medium text-white mb-3">SLO Burn-rate Projection</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-slate-500 uppercase border-b border-slate-700">
                      <th className="text-left py-2 pr-4">SLO</th>
                      <th className="text-left py-2 pr-4">Service</th>
                      <th className="text-right py-2 pr-4">Target</th>
                      <th className="text-right py-2 pr-4">Burn Rate</th>
                      <th className="text-right py-2 pr-4">Budget Remaining</th>
                      <th className="text-right py-2">Days to Exhaust</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.slo_burn
                      .filter((b) => b.burn_rate)
                      .map((b) => (
                        <tr key={b.name} className="border-b border-slate-800 hover:bg-surface-700/30">
                          <td className="py-2 pr-4 text-white">{b.name}</td>
                          <td className="py-2 pr-4 text-slate-400">{b.service || "—"}</td>
                          <td className="py-2 pr-4 text-right text-slate-400">{b.target}%</td>
                          <td className="py-2 pr-4 text-right text-slate-400">{b.burn_rate}</td>
                          <td className="py-2 pr-4 text-right text-slate-400">
                            {b.error_budget_remaining_pct}%
                          </td>
                          <td
                            className={clsx(
                              "py-2 text-right font-medium",
                              b.days_to_exhaustion && b.days_to_exhaustion <= 7
                                ? "text-red-400"
                                : b.days_to_exhaustion && b.days_to_exhaustion <= 14
                                  ? "text-amber-400"
                                  : "text-slate-400"
                            )}
                          >
                            {b.days_to_exhaustion ? `${b.days_to_exhaustion}d` : "—"}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Frequency table */}
          <div className="mt-4">
            <p className="text-sm font-medium text-white mb-3">Incident Frequency (by service)</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 uppercase border-b border-slate-700">
                    <th className="text-left py-2 pr-4">Service</th>
                    <th className="text-right py-2 pr-4">Incidents</th>
                    <th className="text-right py-2 pr-4">MTBF (h)</th>
                    <th className="text-left py-2 pr-4">Patterns</th>
                    <th className="text-left py-2">Last Incident</th>
                  </tr>
                </thead>
                <tbody>
                  {forecast.frequency.map((f) => (
                    <tr key={f.service} className="border-b border-slate-800 hover:bg-surface-700/30">
                      <td className="py-2 pr-4 text-white">{f.service}</td>
                      <td className="py-2 pr-4 text-right text-slate-400">{f.total}</td>
                      <td className="py-2 pr-4 text-right text-slate-400">
                        {f.mtbf_hours ? `${f.mtbf_hours}h` : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(f.by_pattern).map(([pat, cnt]) => (
                            <span
                              key={pat}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-slate-700/50 text-slate-400"
                            >
                              {cnt}x {pat}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-2 text-slate-500 text-xs">
                        {f.last_incident ? new Date(f.last_incident).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Full Resource Catalog */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Search className="w-5 h-5 text-brand-400" />
          Resource Catalog ({catalog?.length ?? 0} items)
        </h2>

        {isLoading ? (
          <div className="animate-pulse text-slate-400 text-sm py-8 text-center">Loading...</div>
        ) : !catalog || catalog.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">No resources yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-500 uppercase border-b border-slate-700">
                  <th className="text-left py-2 pr-4">Type</th>
                  <th className="text-left py-2 pr-4">Name</th>
                  <th className="text-left py-2 pr-4">Service</th>
                  <th className="text-left py-2 pr-4">Pattern / Status</th>
                  <th className="text-left py-2 pr-4">Tags</th>
                  <th className="text-right py-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {catalog.slice(0, 50).map((item) => (
                  <tr key={`${item.type}-${item.id}`} className="border-b border-slate-800 hover:bg-surface-700/30 transition-colors">
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={clsx(
                            "w-5 h-5 rounded flex items-center justify-center",
                            item.type === "incident"
                              ? "bg-red-500/20"
                              : item.type === "report"
                                ? "bg-purple-500/20"
                                : item.type === "runbook"
                                  ? "bg-emerald-500/20"
                                  : item.type === "slo"
                                    ? "bg-cyan-500/20"
                                    : "bg-slate-500/20"
                          )}
                        >
                          {item.type === "incident" ? (
                            <AlertTriangle className="w-3 h-3 text-red-400" />
                          ) : item.type === "report" ? (
                            <FileText className="w-3 h-3 text-purple-400" />
                          ) : item.type === "runbook" ? (
                            <BookOpen className="w-3 h-3 text-emerald-400" />
                          ) : item.type === "slo" ? (
                            <Target className="w-3 h-3 text-cyan-400" />
                          ) : (
                            <Activity className="w-3 h-3 text-slate-400" />
                          )}
                        </span>
                        <span className="text-xs text-slate-400 capitalize">{item.type.replace(/_/g, " ")}</span>
                      </div>
                    </td>
                    <td className="py-2 pr-4">
                      <button
                        onClick={() => {
                          if (item.type === "incident") navigate(`/incidents/${item.id}`);
                        }}
                        className="text-white hover:text-brand-400 transition-colors text-left truncate max-w-[200px]"
                        title={item.name}
                      >
                        {item.name}
                      </button>
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{item.service || "—"}</td>
                    <td className="py-2 pr-4">
                      {item.failure_pattern ? (
                        <span
                          className={clsx(
                            "px-1.5 py-0.5 rounded text-[10px] font-medium",
                            PATTERN_COLORS[item.failure_pattern] || "bg-slate-500/20 text-slate-400"
                          )}
                        >
                          {item.failure_pattern.replace("_", " ")}
                        </span>
                      ) : item.status ? (
                        <span className="text-slate-400 capitalize text-xs">{item.status}</span>
                      ) : (
                        <span className="text-slate-500 text-xs">—</span>
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      <div className="flex flex-wrap gap-1">
                        {(item.tags as string[])?.slice(0, 3).map((t) => (
                          <span
                            key={t}
                            className="px-1 py-0.5 rounded bg-slate-700/50 text-[10px] text-slate-400"
                          >
                            {t}
                          </span>
                        ))}
                        {(item.tags as string[])?.length > 3 && (
                          <span className="text-[10px] text-slate-500">
                            +{(item.tags as string[]).length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2 text-right text-slate-500 text-xs">
                      {item.created_at
                        ? new Date(item.created_at as string).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
