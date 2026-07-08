import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useIncident, useRcaReports, api } from "@/api/client";
import {
  ArrowLeft,
  Clock,
  User,
  MessageSquare,
  FileText,
  Plus,
  Loader2,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { clsx } from "clsx";

type RcaForm = {
  summary: string;
  root_cause: string;
  recommendations: string;
};

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: incident, isLoading } = useIncident(id!);
  const { data: allRcas } = useRcaReports();
  const navigate = useNavigate();

  const [showRcaForm, setShowRcaForm] = useState(false);
  const [rcaForm, setRcaForm] = useState<RcaForm>({
    summary: "",
    root_cause: "",
    recommendations: "",
  });
  const [creatingRca, setCreatingRca] = useState(false);
  const [rcaError, setRcaError] = useState<string | null>(null);

  const [creatingPostmortem, setCreatingPostmortem] = useState(false);
  const [postmortemMsg, setPostmortemMsg] = useState<string | null>(null);

  const rca = allRcas?.find((r) => r.incident_id === id);

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
        <button
          onClick={() => navigate("/incidents")}
          className="text-sm text-brand-400 hover:text-brand-300 mt-2"
        >
          Back to incidents
        </button>
      </div>
    );
  }

  const handleCreateRca = async () => {
    if (!rcaForm.summary.trim() || !rcaForm.root_cause.trim()) return;
    setCreatingRca(true);
    setRcaError(null);
    try {
      await api("/rca", {
        method: "POST",
        body: JSON.stringify({
          incident_id: id,
          summary: rcaForm.summary.trim(),
          root_cause: rcaForm.root_cause.trim(),
          recommendations: rcaForm.recommendations
            .split("\n")
            .map((s) => s.replace(/^\d+[.)]\s*/, "").trim())
            .filter(Boolean),
        }),
      });
      setShowRcaForm(false);
      setRcaForm({ summary: "", root_cause: "", recommendations: "" });
      // Force refetch by navigating away and back
      window.location.reload();
    } catch (err) {
      setRcaError(err instanceof Error ? err.message : "Failed to create RCA");
    } finally {
      setCreatingRca(false);
    }
  };

  const handleCreatePostmortem = async () => {
    setCreatingPostmortem(true);
    setPostmortemMsg(null);
    try {
      await api(`/reports/postmortem/${id}`, { method: "POST" });
      setPostmortemMsg("Postmortem created! Check the Reports page.");
    } catch (err) {
      setPostmortemMsg(
        `Error: ${err instanceof Error ? err.message : "Failed to create postmortem"}`
      );
    } finally {
      setCreatingPostmortem(false);
    }
  };

  const sevColor =
    incident.severity === "SEV-1"
      ? "bg-red-500/20 text-red-400"
      : incident.severity === "SEV-2"
        ? "bg-amber-500/20 text-amber-400"
        : "bg-slate-500/20 text-slate-400";

  const statusColor =
    incident.status === "active"
      ? "bg-red-500/20 text-red-400"
      : incident.status === "stable"
        ? "bg-amber-500/20 text-amber-400"
        : "bg-emerald-500/20 text-emerald-400";

  return (
    <div className="space-y-6">
      {/* Back */}
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
              <span className={clsx("px-2 py-0.5 rounded text-xs font-medium", sevColor)}>
                {incident.severity}
              </span>
              <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium capitalize", statusColor)}>
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

        <div className="flex items-center gap-4 mt-4 text-xs text-slate-500 font-mono">
          <span>ID: {incident.id.slice(0, 12)}&hellip;</span>
          {incident.started_at && (
            <span>Started: {new Date(incident.started_at).toLocaleString()}</span>
          )}
          {incident.resolved_at && (
            <span>Resolved: {new Date(incident.resolved_at).toLocaleString()}</span>
          )}
        </div>
      </div>

      {/* RCA Section */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-brand-400" />
            Root Cause Analysis
          </h2>
          {!rca && !showRcaForm && (
            <button
              onClick={() => setShowRcaForm(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-500/20 text-brand-400 hover:bg-brand-500/30 transition-colors text-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              Request RCA
            </button>
          )}
        </div>

        {rca ? (
          <div className="space-y-3">
            {rca.summary && (
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Summary</p>
                <p className="text-sm text-slate-200">{rca.summary}</p>
              </div>
            )}
            {rca.root_cause && (
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Root Cause</p>
                <p className="text-sm text-slate-300 break-words">{rca.root_cause}</p>
              </div>
            )}
            {rca.recommendations && rca.recommendations.length > 0 && (
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                  Recommendations ({rca.recommendations.length})
                </p>
                <ul className="space-y-1">
                  {rca.recommendations.map((rec, i) => (
                    <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-brand-400 mt-0.5 shrink-0">{i + 1}.</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-xs text-slate-500 pt-2 font-mono">
              Created: {new Date(rca.created_at).toLocaleString()}
            </p>
          </div>
        ) : showRcaForm ? (
          /* RCA Create Form */
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-1 block">
                Summary
              </label>
              <input
                type="text"
                placeholder="Brief summary of root cause"
                value={rcaForm.summary}
                onChange={(e) => setRcaForm({ ...rcaForm, summary: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-slate-600/50 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/50 font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-1 block">
                Root Cause
              </label>
              <textarea
                placeholder="Detailed root cause analysis..."
                rows={4}
                value={rcaForm.root_cause}
                onChange={(e) => setRcaForm({ ...rcaForm, root_cause: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-slate-600/50 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/50 font-mono resize-y"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase tracking-wider mb-1 block">
                Recommendations (one per line)
              </label>
              <textarea
                placeholder="1. First recommendation&#10;2. Second recommendation"
                rows={3}
                value={rcaForm.recommendations}
                onChange={(e) => setRcaForm({ ...rcaForm, recommendations: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-slate-600/50 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/50 font-mono resize-y"
              />
            </div>

            {rcaError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {rcaError}
              </p>
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={handleCreateRca}
                disabled={creatingRca || !rcaForm.summary.trim() || !rcaForm.root_cause.trim()}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-500/20 text-brand-400 hover:bg-brand-500/30 transition-colors text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {creatingRca ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                {creatingRca ? "Creating..." : "Create RCA"}
              </button>
              <button
                onClick={() => {
                  setShowRcaForm(false);
                  setRcaError(null);
                }}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            No RCA report yet. Click &ldquo;Request RCA&rdquo; to create one.
          </p>
        )}
      </div>

      {/* Postmortem Section */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-emerald-400" />
            Postmortem
          </h2>
          <button
            onClick={handleCreatePostmortem}
            disabled={creatingPostmortem}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors text-sm font-medium disabled:opacity-40"
          >
            {creatingPostmortem ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            {creatingPostmortem ? "Generating..." : "Generate Postmortem"}
          </button>
        </div>
        {postmortemMsg && (
          <p
            className={clsx(
              "text-sm flex items-center gap-1.5",
              postmortemMsg.startsWith("Error") ? "text-red-400" : "text-emerald-400"
            )}
          >
            {postmortemMsg.startsWith("Error") ? (
              <AlertTriangle className="w-4 h-4" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            {postmortemMsg}
          </p>
        )}
        {!postmortemMsg && (
          <p className="text-sm text-slate-500">
            Generate a postmortem report from incident + RCA data automatically.
          </p>
        )}
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
                    <span className="px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400 font-mono text-[10px] uppercase">
                      {entry.event_type}
                    </span>
                    {entry.author && (
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {entry.author}
                      </span>
                    )}
                    <span>{new Date(entry.created_at).toLocaleString()}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <MessageSquare className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                    <p className="text-sm text-slate-300">{entry.content ?? entry.event_type}</p>
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
