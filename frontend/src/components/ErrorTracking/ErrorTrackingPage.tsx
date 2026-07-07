import { useErrorTrackers, useErrorEvents } from "@/api/client";
import { useState } from "react";
import { Bug, Search } from "lucide-react";

export function ErrorTrackingPage() {
  const [query, setQuery] = useState("service:api");
  const [input, setInput] = useState("service:api");
  const { data: trackers, isLoading: trackersLoading } = useErrorTrackers();
  const { data: events, isLoading: eventsLoading } = useErrorEvents(query);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Error Tracking</h1>
        <p className="text-sm text-slate-500 mt-1 font-mono">
          Datadog error trackers &mdash; {trackers?.length ?? 0} trackers
        </p>
      </div>

      {/* Trackers */}
      <div>
        <h2 className="text-sm font-mono text-slate-400 mb-3 uppercase tracking-wider">Trackers</h2>
        {trackersLoading ? (
          <div className="animate-pulse text-slate-500 font-mono text-sm">Loading...</div>
        ) : !trackers || trackers.length === 0 ? (
          <div className="glass rounded-xl p-8 text-center">
            <Bug className="w-10 h-10 text-slate-600 mx-auto mb-2" />
            <p className="text-slate-500 font-mono text-sm">No error trackers</p>
            <p className="text-xs text-slate-600 mt-2 font-mono">Errors appear here automatically when Datadog Error Tracking detects issues</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {trackers.map((t) => (
              <div key={t.id} className="glass rounded-lg p-4">
                <p className="text-sm font-medium text-white truncate">{t.attributes?.name ?? t.id}</p>
                <div className="flex items-center gap-3 mt-2 text-xs font-mono">
                  {t.attributes?.count !== undefined && (
                    <span className="text-slate-500">{t.attributes.count} occurrences</span>
                  )}
                  {t.attributes?.status && (
                    <span className={t.attributes.status === "active" ? "text-red-400" : "text-emerald-400"}>
                      {t.attributes.status}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Event search */}
      <div>
        <h2 className="text-sm font-mono text-slate-400 mb-3 uppercase tracking-wider">Recent Events</h2>
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && setQuery(input)}
              placeholder="service:api"
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

        {eventsLoading ? (
          <div className="animate-pulse text-slate-500 font-mono text-sm">Searching...</div>
        ) : !events ? (
          <div className="glass rounded-xl p-8 text-center">
            <p className="text-slate-500 font-mono text-sm">No events found</p>
          </div>
        ) : (
          <pre className="glass rounded-xl p-4 text-xs font-mono text-slate-300 overflow-x-auto max-h-96">
            {JSON.stringify(events, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
