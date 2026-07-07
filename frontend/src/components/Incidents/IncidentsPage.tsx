import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useIncidents } from "@/api/client";
import {
  AlertTriangle,
  Clock,
  CheckCircle2,
  Search,
  Filter,
} from "lucide-react";
import { clsx } from "clsx";

const severityColors: Record<string, string> = {
  "SEV-1": "bg-red-500/20 text-red-400 border-red-500/30",
  "SEV-2": "bg-amber-500/20 text-amber-400 border-amber-500/30",
  "SEV-3": "bg-blue-500/20 text-blue-400 border-blue-500/30",
  "SEV-4": "bg-slate-500/20 text-slate-400 border-slate-500/30",
  "SEV-5": "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

const statusIcons: Record<string, React.ElementType> = {
  active: AlertTriangle,
  stable: Clock,
  resolved: CheckCircle2,
};

const severities = ["SEV-1", "SEV-2", "SEV-3", "SEV-4", "SEV-5"];
const statuses = ["active", "stable", "resolved"];

export function IncidentsPage() {
  const { data: incidents, isLoading } = useIncidents();
  const navigate = useNavigate();

  const [search, setSearch] = useState("");
  const [sevFilter, setSevFilter] = useState<string | null>(null);
  const [statFilter, setStatFilter] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!incidents) return [];
    const q = search.toLowerCase();
    return incidents.filter((inc) => {
      if (q && !inc.title.toLowerCase().includes(q) && !inc.service?.toLowerCase().includes(q))
        return false;
      if (sevFilter && inc.severity !== sevFilter) return false;
      if (statFilter && inc.status !== statFilter) return false;
      return true;
    });
  }, [incidents, search, sevFilter, statFilter]);

  const clearFilters = () => {
    setSearch("");
    setSevFilter(null);
    setStatFilter(null);
  };
  const hasFilters = search || sevFilter || statFilter;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Incidents</h1>
          <p className="text-sm text-slate-400 mt-1">
            Track and manage incidents across your services
          </p>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="glass rounded-xl p-4 space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search by title or service..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface-700 border border-slate-600/50 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/50 font-mono"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          {severities.map((s) => (
            <button
              key={s}
              onClick={() => setSevFilter(sevFilter === s ? null : s)}
              className={clsx(
                "px-2 py-0.5 rounded text-xs font-medium border transition-colors",
                sevFilter === s
                  ? severityColors[s] + " border-current"
                  : "text-slate-500 border-slate-600/50 hover:text-slate-300"
              )}
            >
              {s}
            </button>
          ))}
          <span className="text-slate-600">|</span>
          {statuses.map((st) => (
            <button
              key={st}
              onClick={() => setStatFilter(statFilter === st ? null : st)}
              className={clsx(
                "px-2 py-0.5 rounded text-xs font-medium capitalize transition-colors",
                statFilter === st
                  ? st === "active"
                    ? "bg-red-500/20 text-red-400"
                    : st === "stable"
                    ? "bg-amber-500/20 text-amber-400"
                    : "bg-emerald-500/20 text-emerald-400"
                  : "text-slate-500 hover:text-slate-300"
              )}
            >
              {st}
            </button>
          ))}
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-slate-500 hover:text-slate-300 ml-2"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-pulse text-slate-400">Loading incidents...</div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <p className="text-slate-400">
            {hasFilters ? "No incidents match your filters" : "No incidents recorded yet"}
          </p>
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-brand-400 hover:text-brand-300 mt-2"
            >
              Clear filters
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((inc) => {
            const StatusIcon = statusIcons[inc.status] ?? AlertTriangle;
            return (
              <div
                key={inc.id}
                onClick={() => navigate(`/incidents/${inc.id}`)}
                className="glass rounded-xl p-4 hover:bg-surface-700/80 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div
                      className={clsx(
                        "mt-1 p-1.5 rounded-lg",
                        inc.status === "active"
                          ? "bg-red-500/20 text-red-400"
                          : inc.status === "stable"
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-emerald-500/20 text-emerald-400"
                      )}
                    >
                      <StatusIcon className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-white">
                        {inc.title}
                      </h3>
                      {inc.description && (
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                          {inc.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        <span
                          className={clsx(
                            "px-2 py-0.5 rounded text-xs font-medium border",
                            severityColors[inc.severity] ?? severityColors["SEV-3"]
                          )}
                        >
                          {inc.severity}
                        </span>
                        {inc.service && (
                          <span className="text-xs text-slate-500">
                            {inc.service}
                          </span>
                        )}
                        <span className="text-xs text-slate-500">
                          {new Date(inc.started_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <span
                    className={clsx(
                      "px-2 py-0.5 rounded-full text-xs font-medium capitalize",
                      inc.status === "active"
                        ? "bg-red-500/20 text-red-400"
                        : inc.status === "stable"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-emerald-500/20 text-emerald-400"
                    )}
                  >
                    {inc.status}
                  </span>
                </div>
              </div>
            );
          })}
          <p className="text-xs text-slate-500 text-center pt-2 font-mono">
            {filtered.length} / {incidents?.length ?? 0} incidents
          </p>
        </div>
      )}
    </div>
  );
}
