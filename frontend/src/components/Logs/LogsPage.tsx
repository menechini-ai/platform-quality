import { useDdLogs } from "@/api/client";
import { useState } from "react";
import { Search, FileText } from "lucide-react";

export function LogsPage() {
  const [query, setQuery] = useState("*");
  const [input, setInput] = useState("*");
  const { data: logs, isLoading } = useDdLogs({ query, limit: 50 });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Logs</h1>
          <p className="text-sm text-slate-500 mt-1 font-mono">Datadog log search</p>
        </div>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && setQuery(input)}
            placeholder="service:api status:error"
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface-700 border border-slate-700/50 text-sm text-white placeholder-slate-500 font-mono focus:outline-none focus:border-brand-500/50"
          />
        </div>
        <button
          onClick={() => setQuery(input)}
          className="px-4 py-2 rounded-lg bg-brand-600/20 text-brand-400 text-sm font-mono border border-brand-500/20 hover:bg-brand-600/30 transition-colors"
        >
          Search
        </button>
      </div>

      {isLoading ? (
        <div className="animate-pulse text-slate-500 font-mono text-sm">Searching...</div>
      ) : !logs || logs.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 font-mono text-sm">No logs match</p>
          <p className="text-xs text-slate-600 mt-2 font-mono">Try: <span className="text-brand-400">service:* status:error</span> or <span className="text-brand-400">*</span> for all logs</p>
        </div>
      ) : (
        <div className="space-y-1">
          {logs.map((log) => (
            <div key={log.id} className="glass rounded-lg p-3 font-mono text-xs">
              <div className="flex items-center gap-3 text-slate-500 mb-1">
                <span className="tabular-nums">{new Date(log.timestamp).toISOString()}</span>
                {log.service && <span className="text-brand-400">{log.service}</span>}
                {log.status && (
                  <span className={log.status === "error" || log.status === "critical" ? "text-red-400" : "text-emerald-400"}>
                    {log.status}
                  </span>
                )}
              </div>
              <p className="text-slate-300 leading-relaxed line-clamp-3">{log.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
