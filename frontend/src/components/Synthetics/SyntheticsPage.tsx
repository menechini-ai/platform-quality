import { useSynthetics } from "@/api/client";
import { TestTube, CheckCircle2 } from "lucide-react";

export function SyntheticsPage() {
  const { data: tests, isLoading } = useSynthetics();

  if (isLoading) return <div className="animate-pulse text-slate-500 font-mono text-sm">Loading synthetic tests...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Synthetics</h1>
        <p className="text-sm text-slate-500 mt-1 font-mono">
          Synthetic tests &mdash; {tests?.length ?? 0} total
        </p>
      </div>

      {!tests || tests.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <TestTube className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 font-mono text-sm">No synthetic tests configured</p>
          <p className="text-xs text-slate-600 mt-2 font-mono">Create synthetic tests in Datadog → <span className="text-brand-400">https://app.datadoghq.com/synthetics</span></p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tests.map((t) => (
            <div key={t.public_id} className="glass rounded-xl p-4">
              <div className="flex items-start justify-between mb-2">
                <p className="text-sm font-medium text-white truncate">{t.name}</p>
                <CheckCircle2 className={`w-4 h-4 shrink-0 ${t.status === "live" ? "text-emerald-400" : "text-slate-500"}`} />
              </div>
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="px-1.5 py-0.5 rounded bg-surface-700 text-slate-400">{t.type}</span>
                {t.subtype && <span className="px-1.5 py-0.5 rounded bg-surface-700 text-slate-400">{t.subtype}</span>}
                {t.locations && <span className="text-slate-500">{t.locations.length} locations</span>}
              </div>
              {t.tags && t.tags.length > 0 && (
                <div className="flex gap-1 mt-3 flex-wrap">
                  {t.tags.map((tag) => (
                    <span key={tag} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-700 text-slate-500">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
