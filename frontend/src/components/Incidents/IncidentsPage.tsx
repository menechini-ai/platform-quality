import { useState, useMemo, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useIncidents } from "@/api/client";
import {
  AlertTriangle,
  Clock,
  CheckCircle2,
  Search,
  Eye,
} from "lucide-react";
import { clsx } from "clsx";

import { SegmentedControl } from "@/components/common/SegmentedControl";
import { Pill, SeverityBadge, StatusBadge, SourceBadge } from "@/components/common/Pill";
import { BulkActionBar, RowSelectCheckbox, SelectAllCheckbox, useBulkSelection } from "@/components/common/BulkActionBar";
import { PeekPanel, PeekField, PeekSection } from "@/components/common/PeekPanel";

const severities = ["SEV-1", "SEV-2", "SEV-3", "SEV-4", "SEV-5"];
const statuses = ["active", "stable", "resolved"] as const;

export function IncidentsPage() {
  const { data: incidents, isLoading } = useIncidents();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [q, setQ] = useState("");
  const [peekId, setPeekId] = useState<string | null>(null);

  const status = (searchParams.get("status") ?? "active") as typeof statuses[number];
  const normalizedStatus = statuses.includes(status) ? status : "active";

  // Debounced search
  const [debouncedQ, setDebouncedQ] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  // Origin tab: AI vs webhook (mirror Versus pattern)
  const origin = searchParams.get("origin") ?? "all";

  // Filter pipeline
  const textFiltered = useMemo(() => {
    if (!incidents) return [];
    const query = debouncedQ.toLowerCase().replace(/^#/, "");
    return incidents.filter((inc) => {
      if (query && !inc.title.toLowerCase().includes(query) && !inc.service?.toLowerCase().includes(query)) {
        return false;
      }
      if (origin !== "all" && inc.source !== origin) return false;
      return true;
    });
  }, [incidents, debouncedQ, origin]);

  const counts = useMemo(
    () => ({
      active: textFiltered.filter((i) => i.status === "active").length,
      stable: textFiltered.filter((i) => i.status === "stable").length,
      resolved: textFiltered.filter((i) => i.status === "resolved").length,
    }),
    [textFiltered],
  );

  const filtered = useMemo(
    () => textFiltered.filter((i) => i.status === normalizedStatus),
    [textFiltered, normalizedStatus],
  );

  // Bulk selection
  const bulk = useBulkSelection(filtered, `incidents|${origin}|${normalizedStatus}|${debouncedQ}`);

  const handleBulkAction = (action: string) => {
    const ids = bulk.selectedIds;
    if (ids.length === 0) return;
    if (action === "assign") {
      // TODO: open assign dialog for multiple
    }
    if (action === "resolve") {
      // TODO: bulk resolve
    }
  };

  // Map id → row for peek
  const byId = useMemo(() => new Map(filtered.map((i) => [i.id, i])), [filtered]);

  const peek = peekId ? byId.get(peekId) : undefined;

  const clearFilters = () => {
    setQ("");
    setSearchParams({ status: "active" }, { replace: true });
  };
  const hasFilters = q || normalizedStatus !== "active" || origin !== "all";

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {/* Origin segmented control - primary split */}
        <SegmentedControl
          param="origin"
          defaultValue="all"
          options={[
            { value: "all", label: "All", badge: incidents?.length ?? 0 },
            { value: "agent", label: "AI Detected", badge: incidents?.filter(i => i.source === "agent").length ?? 0 },
            { value: "webhook", label: "Webhook", badge: incidents?.filter(i => i.source === "webhook").length ?? 0 },
          ]}
          ariaLabel="Filter incidents by origin"
        />

        {/* Search */}
        <div className="relative max-w-md flex-1">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search by title, service, or #id..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-surface-700 border border-slate-600/50 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500/50 font-mono"
          />
        </div>
      </div>

      <main className="flex-1 overflow-auto">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {/* Status segmented control with badges */}
          <SegmentedControl
            param="status"
            defaultValue="active"
            options={[
              { value: "active", label: "Active", badge: counts.active },
              { value: "stable", label: "Stable", badge: counts.stable },
              { value: "resolved", label: "Resolved", badge: counts.resolved },
            ]}
            ariaLabel="Filter incidents by status"
          />

          {/* Severity filter pills */}
          <div className="flex items-center gap-1.5 ml-auto">
            <span className="text-xs text-slate-500">Severity:</span>
            {severities.map((s) => (
              <button
                key={s}
                onClick={() => {
                  const next = new URLSearchParams(searchParams);
                  next.set("severity", s);
                  setSearchParams(next, { replace: true });
                }}
                className={clsx(
                  "px-2 py-0.5 rounded text-xs font-medium border transition-colors",
                  searchParams.get("severity") === s
                    ? "bg-brand-500/20 text-brand-400 border-brand-500/30"
                    : "text-slate-500 border-slate-600/50 hover:text-slate-300",
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-pulse text-slate-400 font-mono">Loading incidents...</div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="glass rounded-xl p-12 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <p className="text-slate-400 font-mono text-sm">
              {hasFilters ? "No incidents match your filters" : "No incidents recorded yet"}
            </p>
            {hasFilters && (
              <button
                onClick={clearFilters}
                className="text-sm text-brand-400 hover:text-brand-300 mt-2 font-mono"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <>
            {/* Table header */}
            <div className="grid grid-cols-[40px_1fr_auto_auto_auto_40px] gap-3 px-2 pb-2 text-xs font-medium text-slate-500 border-b border-slate-700/50 font-mono">
              <SelectAllCheckbox checked={bulk.allSelected} indeterminate={bulk.someSelected} onChange={bulk.toggleAll} />
              <span>Service / Title</span>
              <span className="w-24">Severity</span>
              <span className="w-20">Status</span>
              <span className="w-28">When</span>
              <span>Source</span>
            </div>

            {/* Rows */}
            <div className="space-y-1">
              {filtered.map((inc) => {
                const selected = bulk.isSelected(inc.id);
                return (
                  <div
                    key={inc.id}
                    onClick={() => {
                      setPeekId(inc.id);
                    }}
                    className={clsx(
                      "grid grid-cols-[40px_1fr_auto_auto_auto_40px] gap-3 px-2 py-2.5 rounded-lg",
                      "transition-colors cursor-pointer",
                      selected && "bg-brand-500/10 border border-brand-500/30",
                      "hover:bg-surface-700/50",
                    )}
                  >
                    <RowSelectCheckbox
                      checked={selected}
                      onChange={() => bulk.toggleOne(inc.id)}
                      aria-label={`Select incident ${inc.title}`}
                    />

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-medium text-white truncate">{inc.title || `#${inc.id.slice(0, 8)}`}</h3>
                        {inc.source && <SourceBadge source={inc.source} />}
                      </div>
                      {inc.service && (
                        <p className="text-xs text-slate-500 truncate font-mono">{inc.service}</p>
                      )}
                      {inc.description && (
                        <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{inc.description}</p>
                      )}
                    </div>

                    <SeverityBadge severity={inc.severity} className="w-24 justify-center" />
                    <StatusBadge status={inc.status} className="w-20 justify-center" />
                    <span className="text-xs text-slate-400 font-mono w-28">
                      {new Date(inc.started_at).toLocaleString()}
                    </span>

                    <div className="flex items-center justify-end pr-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setPeekId(inc.id);
                        }}
                        className="p-1 rounded hover:bg-surface-700 text-slate-500 hover:text-white transition-colors"
                        aria-label="View details"
                      >
                        <Eye size={14} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Count footer */}
            <p className="text-xs text-slate-500 text-center pt-2 font-mono">
              {filtered.length} / {textFiltered.length} incidents
            </p>
          </>
        )}

        {/* Bulk action bar */}
        <BulkActionBar
          selectedIds={bulk.selectedIds}
          onClear={bulk.clear}
          onAction={handleBulkAction}
          actions={[
            { id: "assign", label: "Assign" },
            { id: "resolve", label: "Resolve" },
          ]}
        />

        {/* Peek panel - slide-out detail */}
        <PeekPanel isOpen={!!peekId} onClose={() => setPeekId(null)} title="Incident Details">
          {peek && (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-medium text-white flex-1">{peek.title || `#${peek.id.slice(0, 8)}`}</h2>
                <SeverityBadge severity={peek.severity} />
                <StatusBadge status={peek.status} />
                {peek.source && <SourceBadge source={peek.source} />}
              </div>

              <PeekSection title="Identifiers">
                <PeekField label="ID" value={peek.id} copyable />
                {peek.dd_id && <PeekField label="Datadog ID" value={peek.dd_id} copyable />}
              </PeekSection>

              <PeekSection title="Timeline">
                <PeekField label="Started" value={new Date(peek.started_at).toISOString()} />
                {peek.resolved_at && <PeekField label="Resolved" value={new Date(peek.resolved_at).toISOString()} />}
                <PeekField label="Created" value={new Date(peek.created_at).toISOString()} />
              </PeekSection>

              {peek.service && (
                <PeekSection title="Service">
                  <PeekField label="Service" value={peek.service} />
                </PeekSection>
              )}

              {peek.tags?.length && (
                <PeekSection title="Tags">
                  <div className="flex flex-wrap gap-1">
                    {peek.tags.map((t) => (
                      <Pill key={t} tone="default" className="text-[10px]">
                        {t}
                      </Pill>
                    ))}
                  </div>
                </PeekSection>
              )}

              {peek.description && (
                <PeekSection title="Description">
                  <p className="text-sm text-slate-300 whitespace-pre-wrap">{peek.description}</p>
                </PeekSection>
              )}

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-700/50">
                <button
                  onClick={() => navigate(`/incidents/${peek.id}`)}
                  className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium"
                >
                  Open Full Details
                </button>
              </div>
            </div>
          )}
        </PeekPanel>
      </main>
    </>
  );
}