import { useState } from "react";
import { useDdSlos } from "@/api/client";
import { Sigma, CheckCircle2 } from "lucide-react";

export function SlosPage() {
  const [tagsFilter, setTagsFilter] = useState("");
  const { data: slos, isLoading } = useDdSlos(
    tagsFilter ? { tags: tagsFilter } : undefined,
  );

  if (isLoading) return <div className="animate-pulse text-slate-500 font-mono text-sm">Loading SLOs...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">SLOs</h1>
          <p className="text-sm text-slate-500 mt-1 font-mono">Service Level Objectives — {slos?.length ?? 0} total</p>
        </div>
        <input
          type="text"
          value={tagsFilter}
          onChange={(e) => setTagsFilter(e.target.value)}
          placeholder="Tags (e.g. env:prod,service:api)"
          className="px-3 py-2 rounded-lg bg-surface-800 border border-surface-600
                     text-white text-sm placeholder:text-slate-500 w-72
                     focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {!slos || slos.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <Sigma className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 font-mono text-sm">No SLOs defined</p>
          <p className="text-xs text-slate-600 mt-2 font-mono">Create SLOs in Datadog → <span className="text-brand-400">https://app.datadoghq.com/slo</span></p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {slos.map((slo) => {
            const target = slo.thresholds?.[0]?.target ?? slo.target;
            const pct = (target * 100);
            const status = slo.overall_status ?? "breached";
            const ok = status === "breached";
            return (
              <div key={slo.id} className="glass rounded-xl p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{slo.name}</p>
                    {slo.description && <p className="text-xs text-slate-500 mt-1 line-clamp-2">{slo.description}</p>}
                    {slo.tags && slo.tags.length > 0 && (
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {slo.tags.map((t) => (
                          <span key={t} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-700 text-slate-500">{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <CheckCircle2 className={`w-5 h-5 shrink-0 ${ok ? "text-red-400" : "text-emerald-400"}`} />
                </div>
                <div className="flex items-end justify-between">
                  <span className="text-slate-500 text-xs font-mono">target</span>
                  <span className="text-2xl font-bold font-mono tabular-nums text-white">{pct}%</span>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-surface-700 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${ok ? "bg-red-400" : "bg-emerald-400"}`}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
