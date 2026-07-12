import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { EmptyHint, JsonView, StatePanel } from "@/components/common/JsonView";

export function RumPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dd-rum"],
    queryFn: () => api<unknown>("/datadog/rum"),
    retry: 1,
  });

  const isEmpty =
    data == null ||
    (Array.isArray(data) && data.length === 0) ||
    (typeof data === "object" && Object.keys(data as object).length === 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">RUM</h1>
        <p className="text-sm text-slate-500 mt-1 font-mono">
          Real User Monitoring sessions
        </p>
      </div>

      <StatePanel isLoading={isLoading} isError={isError} error={error}>
        <div className="glass rounded-xl p-4">
          {isEmpty ? <EmptyHint label="RUM sessions" /> : <JsonView data={data} />}
        </div>
      </StatePanel>
    </div>
  );
}
