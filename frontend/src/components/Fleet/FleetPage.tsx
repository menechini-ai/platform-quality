import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { EmptyHint, JsonView, StatePanel } from "@/components/common/JsonView";

type Agent = { id: string; [key: string]: unknown };

export function FleetPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dd-fleet"],
    queryFn: () => api<Agent[] | unknown>("/datadog/fleet/agents"),
    retry: 1,
  });

  const detail = useQuery({
    queryKey: ["dd-fleet-agent", selected],
    queryFn: () => api<unknown>(`/datadog/fleet/agents/${selected}`),
    enabled: selected !== null,
    retry: 1,
  });

  const agents = Array.isArray(data) ? (data as Agent[]) : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Fleet</h1>
        <p className="text-sm text-slate-500 mt-1 font-mono">Datadog Agent fleet</p>
      </div>

      <StatePanel isLoading={isLoading} isError={isError} error={error}>
        {agents.length === 0 ? (
          <div className="glass rounded-xl p-4">
            <EmptyHint label="agents" />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="glass rounded-xl p-4 space-y-2">
              {agents.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setSelected(a.id)}
                  className={
                    selected === a.id
                      ? "w-full text-left rounded-lg bg-brand-600/20 px-3 py-2 text-sm font-mono text-brand-200"
                      : "w-full text-left rounded-lg bg-surface-800/50 px-3 py-2 text-sm font-mono text-slate-300 hover:text-white"
                  }
                >
                  {a.id}
                </button>
              ))}
            </div>
            <div className="glass rounded-xl p-4">
              {selected === null ? (
                <p className="text-slate-500 font-mono text-sm">Select an agent to inspect.</p>
              ) : detail.isLoading ? (
                <div className="animate-pulse text-slate-500 font-mono text-sm">
                  Loading agent…
                </div>
              ) : detail.isError ? (
                <p className="text-red-400 font-mono text-sm">
                  Failed: {(detail.error as Error)?.message}
                </p>
              ) : (
                <JsonView data={detail.data} />
              )}
            </div>
          </div>
        )}
      </StatePanel>
    </div>
  );
}
