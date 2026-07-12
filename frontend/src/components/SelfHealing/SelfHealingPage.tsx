import { useState } from "react";
import {
  useRunbooks,
  useActions,
  useApproveAction,
  useRejectAction,
  useAnalyzeSelfHealing,
  type AnalysisResult,
} from "@/api/client";
import {
  Wrench,
  BookOpen,
  History,
  CheckCircle2,
  XCircle,
  Activity,
  Loader2,
  AlertTriangle,
  CheckCheck,
  Ban,
} from "lucide-react";

const statusColors: Record<string, string> = {
  pending: "bg-yellow-500/20 text-yellow-400",
  approved: "bg-blue-500/20 text-blue-400",
  rejected: "bg-red-500/20 text-red-400",
  running: "bg-purple-500/20 text-purple-400",
  success: "bg-emerald-500/20 text-emerald-400",
  failed: "bg-red-500/20 text-red-400",
};

const statusFilters = [
  { label: "All", value: "" },
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
  { label: "Failed", value: "failed" },
];

export function SelfHealingPage() {
  const [actionFilter, setActionFilter] = useState("");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [tagsFilter, setTagsFilter] = useState("");

  const { data: runbooks, isLoading: runbooksLoading } = useRunbooks();
  const { data: actions, isLoading: actionsLoading } = useActions(
    actionFilter ? { status: actionFilter } : undefined,
  );
  const approveAction = useApproveAction();
  const rejectAction = useRejectAction();
  const analyze = useAnalyzeSelfHealing();

  const handleAnalyze = async () => {
    const result = await analyze.mutateAsync(tagsFilter || undefined);
    setAnalysisResult(result);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Self-Healing</h1>
          <p className="text-sm text-slate-400 mt-1">
            Automated remediation runbooks, action history, and SRE health analysis
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={tagsFilter}
            onChange={(e) => setTagsFilter(e.target.value)}
            placeholder='Tags (e.g. service:api-gateway,env:prod)'
            className="px-3 py-2 rounded-lg bg-surface-800 border border-surface-600
                       text-white text-sm placeholder:text-slate-500 w-72
                       focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            onClick={handleAnalyze}
            disabled={analyze.isPending}
            className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-50
                       text-white text-sm font-medium flex items-center gap-2 transition-colors"
          >
            {analyze.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Activity className="w-4 h-4" />
            )}
            Run SRE Analysis
          </button>
        </div>
      </div>

      {/* SRE Analysis Results */}
      {analysisResult && (
        <div className="glass rounded-xl p-5">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-brand-400" />
            Latest SRE Analysis
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="p-3 rounded-lg bg-surface-700/50 text-center">
              <p className="text-2xl font-bold text-white">{analysisResult.score ?? "N/A"}</p>
              <p className="text-xs text-slate-400">Health Score</p>
            </div>
            <div className="p-3 rounded-lg bg-surface-700/50 text-center">
              <p className="text-2xl font-bold text-white capitalize">
                {analysisResult.severity ?? "unknown"}
              </p>
              <p className="text-xs text-slate-400">Severity</p>
            </div>
            <div className="p-3 rounded-lg bg-surface-700/50 text-center">
              <p className="text-2xl font-bold text-white">
                {analysisResult.recommendations?.length ?? 0}
              </p>
              <p className="text-xs text-slate-400">Recommendations</p>
            </div>
          </div>
          {analysisResult.summary && (
            <p className="text-sm text-slate-300 mb-3">{analysisResult.summary}</p>
          )}
          {analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Recommendations
              </p>
              {analysisResult.recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-sm text-slate-300"
                >
                  <AlertTriangle className="w-4 h-4 mt-0.5 text-amber-400 shrink-0" />
                  <span>{rec}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Runbooks */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-brand-400" />
          Runbooks
        </h2>

        {runbooksLoading ? (
          <p className="text-slate-400 text-sm text-center py-8">Loading...</p>
        ) : !runbooks || runbooks.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">
            No runbooks configured yet
          </p>
        ) : (
          <div className="space-y-3">
            {runbooks.map((rb) => (
              <div
                key={rb.id}
                className="p-4 rounded-lg bg-surface-700/50"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Wrench className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="text-sm font-medium text-white">
                        {rb.name}
                      </p>
                      {rb.description && (
                        <p className="text-xs text-slate-400">
                          {rb.description}
                        </p>
                      )}
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      rb.is_active
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-slate-500/20 text-slate-400"
                    }`}
                  >
                    {rb.is_active ? "Active" : "Inactive"}
                  </span>
                </div>

                <div className="mt-3 flex items-center gap-2">
                  <span className="text-xs text-slate-500">
                    {rb.steps.length} step(s)
                  </span>
                  {rb.triggers && (
                    <span className="text-xs text-slate-500">
                      &bull; Auto-trigger enabled
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action History */}
      <div className="glass rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-brand-400" />
            Action History
          </h2>
          <div className="flex gap-1.5">
            {statusFilters.map((f) => (
              <button
                key={f.value}
                onClick={() => setActionFilter(f.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  actionFilter === f.value
                    ? "bg-brand-600 text-white"
                    : "bg-surface-700 text-slate-400 hover:text-white"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {actionsLoading ? (
          <p className="text-slate-400 text-sm text-center py-8">Loading...</p>
        ) : !actions || actions.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">
            No auto-heal actions yet
          </p>
        ) : (
          <div className="space-y-2">
            {actions.map((action) => (
              <div
                key={action.id}
                className="flex items-center justify-between p-3 rounded-lg bg-surface-700/50"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {action.status === "success" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : action.status === "failed" || action.status === "rejected" ? (
                    <XCircle className="w-4 h-4 text-red-400 shrink-0" />
                  ) : (
                    <History className="w-4 h-4 text-amber-400 shrink-0" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm text-white capitalize">
                      {action.action_type}
                      {action.action_config?.runbook
                        ? ` — ${action.action_config.runbook as string}`
                        : ""}
                    </p>
                    <p className="text-xs text-slate-500">
                      {new Date(action.requested_at).toLocaleString()}
                      {action.action_config?.trigger_reason
                        ? ` — ${action.action_config.trigger_reason as string}`
                        : ""}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      statusColors[action.status] ?? "bg-slate-500/20 text-slate-400"
                    }`}
                  >
                    {action.status}
                  </span>
                  {action.status === "pending" && (
                    <>
                      <button
                        onClick={() => approveAction.mutate(action.id)}
                        disabled={approveAction.isPending}
                        className="p-1.5 rounded-md bg-emerald-500/20 text-emerald-400
                                   hover:bg-emerald-500/30 disabled:opacity-50 transition-colors"
                        title="Approve"
                      >
                        <CheckCheck className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => rejectAction.mutate(action.id)}
                        disabled={rejectAction.isPending}
                        className="p-1.5 rounded-md bg-red-500/20 text-red-400
                                   hover:bg-red-500/30 disabled:opacity-50 transition-colors"
                        title="Reject"
                      >
                        <Ban className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
