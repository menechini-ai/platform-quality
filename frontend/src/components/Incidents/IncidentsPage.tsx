import { useState, useMemo, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useIncidents } from "@/api/client";
import {
  CheckCircle2,
  Search,
  Eye,
} from "lucide-react";
import { clsx } from "clsx";

import { SegmentedControl } from "@/components/common/SegmentedControl";
import { Pill, SeverityBadge, StatusBadge, SourceBadge } from "@/components/common/Pill";
import { BulkActionBar, RowSelectCheckbox, SelectAllCheckbox } from "@/components/common/BulkActionBar";
import { useBulkSelection } from "@/hooks/useBulkSelection";
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
  const bulk = useBulkSelection({
    items: filtered,
    storageKey: `incidents|${origin}|${normalizedStatus}|${debouncedQ}`,
  });

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
            { value: "agent", label: "AI Detected", badge: incidents?.filter((i) => i.source === "agent").length ?? 0 },
            { value: "webhook", label: "Webhook", badge: incidents?.filter((i) => i.source === "webhook").length ?? 0 },
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
            className="input w-full pl-9"
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
                  "pill",
                  searchParams.get("severity") === s
                    ? "pill-accent"
                    : "pill-default hover:pill-accent",
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
          <div className="card p-12 text-center">
            <CheckCircle2 className="w-12 h-12 text-[rgb(var(--sev-ok))] mx-auto mb-3" />
            <p className="text-slate-400 font-mono text-sm">
              {hasFilters ? "No incidents match your filters" : "No incidents recorded yet"}
            </p>
            {hasFilters && (
              <button
                onClick={clearFilters}
                className="text-sm text-[rgb(var(--brand))] hover:text-[rgb(var(--brand))] mt-2 font-mono"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <>
            {/* Table header */}
            <div className="ddt">
              <thead>
                <tr>
                  <th className="w-10"><SelectAllCheckbox checked={bulk.allSelected} indeterminate={bulk.someSelected} onChange={bulk.toggleAll} /></th>
                  <th>Service / Title</th>
                  <th className="w-24">Severity</th>
                  <th className="w-20">Status</th>
                  <th className="w-28">When</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((inc, idx) => {
                  const selected = bulk.isSelected(inc.id);
                  return (
                    <tr
                      key={inc.id}
                      className={clsx(
                        selected && "bg-[rgb(var(--brand)/0.1)]",
                        "hover:bg-[rgb(var(--ink-700)/0.4)]",
                        "cursor-pointer",
                        "animate-row-in",
                      )}
                      style={{ animationDelay: `${Math.min(idx, 11) * 25}ms` }}
                      onClick={() => setPeekId(inc.id)}
                    >
                      <td className="w-10">
                        <RowSelectCheckbox
                          checked={selected}
                          onChange={() => bulk.toggleOne(inc.id)}
                          aria-label={`Select incident ${inc.title}`}
                        />
                      </td>
                      <td className="min-w-0">
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
                      </td>
                      <td className="w-24">
                        <SeverityBadge severity={inc.severity} className="justify-center" />
                      </td>
                      <td className="w-20">
                        <StatusBadge status={inc.status} className="justify-center" />
                      </td>
                      <td className="w-28 text-xs text-slate-400 font-mono">
                        {new Date(inc.started_at).toLocaleString()}
                      </td>
                      <td className="flex items-center justify-end pr-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setPeekId(inc.id);
                          }}
                          className="btn btn-ghost p-1"
                          aria-label="View details"
                        >
                          <Eye size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
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

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-[rgb(var(--ink-700)/0.5)]">
                <button
                  onClick={() => navigate(`/incidents/${peek.id}`)}
                  className="btn btn-primary"
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