import { useRunbooks, useActions } from "@/api/client";
import { Wrench, BookOpen, History, CheckCircle2, XCircle } from "lucide-react";

const statusColors: Record<string, string> = {
  pending: "bg-yellow-500/20 text-yellow-400",
  approved: "bg-blue-500/20 text-blue-400",
  rejected: "bg-red-500/20 text-red-400",
  running: "bg-purple-500/20 text-purple-400",
  success: "bg-emerald-500/20 text-emerald-400",
  failed: "bg-red-500/20 text-red-400",
};

export function SelfHealingPage() {
  const { data: runbooks } = useRunbooks();
  const { data: actions } = useActions();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Self-Healing</h1>
        <p className="text-sm text-slate-400 mt-1">
          Automated remediation runbooks and action history
        </p>
      </div>

      {/* Runbooks */}
      <div className="glass rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-brand-400" />
          Runbooks
        </h2>

        {!runbooks || runbooks.length === 0 ? (
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
                      • Auto-trigger enabled
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
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <History className="w-5 h-5 text-brand-400" />
          Action History
        </h2>

        {!actions || actions.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">
            No auto-heal actions executed yet
          </p>
        ) : (
          <div className="space-y-2">
            {actions.map((action) => (
              <div
                key={action.id}
                className="flex items-center justify-between p-3 rounded-lg bg-surface-700/50"
              >
                <div className="flex items-center gap-3">
                  {action.status === "success" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : action.status === "failed" || action.status === "rejected" ? (
                    <XCircle className="w-4 h-4 text-red-400" />
                  ) : (
                    <History className="w-4 h-4 text-amber-400" />
                  )}
                  <div>
                    <p className="text-sm text-white capitalize">
                      {action.action_type}
                    </p>
                    <p className="text-xs text-slate-500">
                      {new Date(action.requested_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    statusColors[action.status] ?? "bg-slate-500/20 text-slate-400"
                  }`}
                >
                  {action.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
