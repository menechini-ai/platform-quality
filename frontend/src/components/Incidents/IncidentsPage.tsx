import { useNavigate } from "react-router-dom";
import { useIncidents } from "@/api/client";
import { AlertTriangle, Clock, CheckCircle2 } from "lucide-react";

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

export function IncidentsPage() {
  const { data: incidents, isLoading } = useIncidents();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-slate-400">Loading incidents...</div>
      </div>
    );
  }

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

      {!incidents || incidents.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <p className="text-slate-400">No incidents recorded yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map((inc) => {
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
                      className={`mt-1 p-1.5 rounded-lg ${
                        inc.status === "active"
                          ? "bg-red-500/20 text-red-400"
                          : inc.status === "stable"
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-emerald-500/20 text-emerald-400"
                      }`}
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
                          className={`px-2 py-0.5 rounded text-xs font-medium border ${
                            severityColors[inc.severity] ?? severityColors["SEV-3"]
                          }`}
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
                    className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                      inc.status === "active"
                        ? "bg-red-500/20 text-red-400"
                        : inc.status === "stable"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-emerald-500/20 text-emerald-400"
                    }`}
                  >
                    {inc.status}
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
