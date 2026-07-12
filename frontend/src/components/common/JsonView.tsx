import type { ReactNode } from "react";

import { clsx } from "clsx";

/** Renders unknown Datadog-shaped JSON as a table (arrays of objects) or code. */
export function JsonView({ data }: { data: unknown }) {
  if (data === null || data === undefined) {
    return <span className="text-slate-600 font-mono text-xs">null</span>;
  }

  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-slate-600 font-mono text-xs">[]</span>;
    if (data.every((d) => typeof d === "object" && d !== null)) {
      const keys = Array.from(
        new Set(data.flatMap((d) => Object.keys(d as Record<string, unknown>))),
      ).slice(0, 8);
      return (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr>
                {keys.map((k) => (
                  <th
                    key={k}
                    className="px-3 py-2 text-slate-400 border-b border-surface-700 whitespace-nowrap"
                  >
                    {k}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i} className="even:bg-surface-800/40">
                  {keys.map((k) => (
                    <td
                      key={k}
                      className="px-3 py-2 text-slate-300 max-w-xs truncate"
                    >
                      {String((row as Record<string, unknown>)[k] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    return (
      <ul className="text-xs font-mono text-slate-300 space-y-1">
        {data.map((d, i) => (
          <li key={i}>{String(d)}</li>
        ))}
      </ul>
    );
  }

  if (typeof data === "object") {
    const rows = Object.entries(data as Record<string, unknown>).map(([k, v]) => ({
      key: k,
      value: typeof v === "object" ? JSON.stringify(v) : String(v),
    }));
    return <JsonView data={rows} />;
  }

  return <span className="text-xs font-mono text-slate-300">{String(data)}</span>;
}

export function StatePanel({
  isLoading,
  isError,
  error,
  children,
}: {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  children: ReactNode;
}) {
  if (isLoading) {
    return (
      <div className="animate-pulse text-slate-500 font-mono text-sm">Loading…</div>
    );
  }
  if (isError) {
    return (
      <div className="glass rounded-xl p-6 text-red-400 font-mono text-sm">
        Failed to load: {(error as Error)?.message ?? "unknown error"}
      </div>
    );
  }
  return <>{children}</>;
}

export function EmptyHint({ label }: { label: string }) {
  return (
    <p className={clsx("text-slate-500 font-mono text-sm")}>
      No {label}. Connect a Datadog source to populate this view.
    </p>
  );
}
