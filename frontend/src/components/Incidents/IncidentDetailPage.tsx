import { useParams, useNavigate } from "react-router-dom";
import { useIncident } from "@/api/client";
import { ArrowLeft, Clock, User, MessageSquare } from "lucide-react";

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: incident, isLoading } = useIncident(id!);
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-slate-400">Loading incident...</div>
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="glass rounded-xl p-12 text-center">
        <p className="text-slate-400">Incident not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate("/incidents")}
        className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to incidents
      </button>

      {/* Header */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  incident.severity === "SEV-1"
                    ? "bg-red-500/20 text-red-400"
                    : incident.severity === "SEV-2"
                    ? "bg-amber-500/20 text-amber-400"
                    : "bg-slate-500/20 text-slate-400"
                }`}
              >
                {incident.severity}
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                  incident.status === "active"
                    ? "bg-red-500/20 text-red-400"
                    : incident.status === "stable"
                    ? "bg-amber-500/20 text-amber-400"
                    : "bg-emerald-500/20 text-emerald-400"
                }`}
              >
                {incident.status}
              </span>
            </div>
            <h1 className="text-xl font-bold text-white">{incident.title}</h1>
            {incident.service && (
              <p className="text-sm text-slate-400 mt-1">{incident.service}</p>
            )}
          </div>
        </div>

        {incident.description && (
          <p className="text-sm text-slate-300 mt-4">{incident.description}</p>
        )}

        <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
          <span>Started: {new Date(incident.started_at).toLocaleString()}</span>
          {incident.resolved_at && (
            <span>
              Resolved: {new Date(incident.resolved_at).toLocaleString()}
            </span>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-brand-400" />
          Timeline
        </h2>

        {incident.timeline.length === 0 ? (
          <p className="text-slate-400 text-sm">No timeline entries yet</p>
        ) : (
          <div className="space-y-4">
            {incident.timeline.map((entry) => (
              <div key={entry.id} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-2 h-2 rounded-full bg-brand-500 mt-2" />
                  <div className="flex-1 w-px bg-slate-700" />
                </div>
                <div className="flex-1 pb-4">
                  <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                    {entry.author && (
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {entry.author}
                      </span>
                    )}
                    <span>
                      {new Date(entry.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-start gap-2">
                    <MessageSquare className="w-4 h-4 text-slate-500 mt-0.5" />
                    <p className="text-sm text-slate-300">
                      {entry.content ?? entry.event_type}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
