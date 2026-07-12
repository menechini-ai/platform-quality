import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { EmptyHint, JsonView, StatePanel } from "@/components/common/JsonView";

type TabId = "services" | "spans" | "resources" | "dependencies";

const TABS: { id: TabId; label: string; path: string }[] = [
  { id: "services", label: "Services", path: "/datadog/apm/services" },
  { id: "spans", label: "Spans", path: "/datadog/apm/spans" },
  { id: "resources", label: "Resources", path: "/datadog/apm/resources" },
  { id: "dependencies", label: "Dependencies", path: "/datadog/apm/dependencies?days=7" },
];

export function ApmPage() {
  const [tab, setTab] = useState<TabId>("services");
  const active = TABS.find((t) => t.id === tab) ?? TABS[0];

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["apm", tab],
    queryFn: () => api<unknown>(active.path),
    retry: 1,
  });

  const isEmpty =
    data == null ||
    (Array.isArray(data) && data.length === 0) ||
    (typeof data === "object" && Object.keys(data as object).length === 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">APM</h1>
        <p className="text-sm text-slate-500 mt-1 font-mono">
          Application Performance Monitoring
        </p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={
              tab === t.id
                ? "px-3 py-1.5 rounded-lg text-sm font-mono bg-brand-600/30 text-brand-200"
                : "px-3 py-1.5 rounded-lg text-sm font-mono bg-surface-800 text-slate-400 hover:text-slate-200"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      <StatePanel isLoading={isLoading} isError={isError} error={error}>
        <div className="glass rounded-xl p-4">
          {isEmpty ? <EmptyHint label="APM data" /> : <JsonView data={data} />}
        </div>
      </StatePanel>
    </div>
  );
}
