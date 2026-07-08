import { useDdMetrics, type DdMetricPoint } from "@/api/client";
import { LineChart } from "lucide-react";
import { useState } from "react";

const COMMON_METRICS = [
  "system.cpu.user",
  "system.mem.used",
  "system.disk.used",
  "system.net.bytes_rcvd",
  "system.net.bytes_sent",
  "aws.ec2.cpuutilization",
  "aws.rds.database_connections",
  "redis.cpu.user",
  "nginx.requests.total",
  "puma.max_threads",
];

export function MetricsPage() {
  const [metric, setMetric] = useState(COMMON_METRICS[0]);
  const [tagInput, setTagInput] = useState("*");
  const { data, isLoading } = useDdMetrics({
    metric,
    agg: "avg",
    tags: tagInput,
    days: 1,
  });

  const series = data?.resp;
  const rows = series?.series ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Metrics</h1>
        <p className="text-sm text-slate-500 mt-1 font-mono">Datadog timeseries queries</p>
      </div>

      <div className="glass rounded-xl p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-500 font-mono mb-1 block">Metric</label>
            <input
              type="text"
              defaultValue={metric}
              onKeyDown={(e) => { if (e.key === "Enter") setMetric((e.target as HTMLInputElement).value); }}
              list="common-metrics"
              placeholder="system.cpu.user"
              className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-slate-700/50 text-sm text-white font-mono focus:outline-none focus:border-brand-500/50"
            />
            <datalist id="common-metrics">
              {COMMON_METRICS.map((m) => <option key={m} value={m} />)}
            </datalist>
          </div>
          <div>
            <label className="text-xs text-slate-500 font-mono mb-1 block">Tags</label>
            <input
              type="text"
              defaultValue={tagInput}
              onKeyDown={(e) => { if (e.key === "Enter") setTagInput((e.target as HTMLInputElement).value); }}
              placeholder="service:api,env:prod"
              className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-slate-700/50 text-sm text-white font-mono focus:outline-none focus:border-brand-500/50"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="animate-pulse text-slate-500 font-mono text-sm">Querying...</div>
      ) : rows.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <LineChart className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 font-mono text-sm">No data for {metric}</p>
          <p className="text-xs text-slate-600 mt-2 font-mono">Check metric name in <span className="text-brand-400">Datadog Metrics Summary</span> or try <span className="text-brand-400">system.cpu.user</span></p>
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map((s: { metric: string; points: DdMetricPoint[] }, i: number) => {
            const vals = (s.points ?? [])
              .map((p: DdMetricPoint) => p.value)
              .filter((v: number | null | undefined) => v != null);
            const avg = vals.length > 0 ? (vals.reduce((a: number, b: number) => a + b, 0) / vals.length).toFixed(2) : "—";
            const max = vals.length > 0 ? Math.max(...vals).toFixed(2) : "—";
            const min = vals.length > 0 ? Math.min(...vals).toFixed(2) : "—";
            return (
              <div key={i} className="glass rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-mono text-white">{s.metric}</p>
                  <span className="text-xs text-slate-500 font-mono">{s.points?.length ?? 0} points</span>
                </div>
                <div className="flex gap-4 text-xs font-mono">
                  <span className="text-slate-500">avg <span className="text-white">{avg}</span></span>
                  <span className="text-slate-500">max <span className="text-white">{max}</span></span>
                  <span className="text-slate-500">min <span className="text-white">{min}</span></span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
