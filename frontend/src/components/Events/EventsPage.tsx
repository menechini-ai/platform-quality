import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { EmptyHint, StatePanel } from "@/components/common/JsonView";

type EventRow = { id: number; title?: string; text?: string };

export function EventsPage() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dd-events"],
    queryFn: () => api<EventRow[] | unknown>("/datadog/events"),
    retry: 1,
  });

  const create = useMutation({
    mutationFn: () =>
      api("/datadog/events", {
        method: "POST",
        body: JSON.stringify({ title, text }),
      }),
    onSuccess: () => {
      setTitle("");
      setText("");
      void qc.invalidateQueries({ queryKey: ["dd-events"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api(`/datadog/events/${id}`, { method: "DELETE" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["dd-events"] }),
  });

  const events = Array.isArray(data) ? (data as EventRow[]) : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Events</h1>
        <p className="text-sm text-slate-500 mt-1 font-mono">Datadog events stream</p>
      </div>

      <div className="glass rounded-xl p-4 space-y-3">
        <div className="flex gap-2 flex-wrap">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Event title"
            className="flex-1 min-w-[180px] bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder:text-slate-600"
          />
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Event text"
            className="flex-1 min-w-[180px] bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder:text-slate-600"
          />
          <button
            type="button"
            disabled={!title || create.isPending}
            onClick={() => create.mutate()}
            className="px-4 py-2 rounded-lg text-sm font-mono bg-brand-600/30 text-brand-200 disabled:opacity-40"
          >
            Create
          </button>
        </div>
      </div>

      <StatePanel isLoading={isLoading} isError={isError} error={error}>
        {events.length === 0 ? (
          <div className="glass rounded-xl p-4">
            <EmptyHint label="events" />
          </div>
        ) : (
          <div className="glass rounded-xl p-4 space-y-2">
            {events.map((ev) => (
              <div
                key={ev.id}
                className="flex items-center justify-between gap-3 rounded-lg bg-surface-800/50 p-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {ev.title ?? `#${ev.id}`}
                  </p>
                  {ev.text && (
                    <p className="text-xs text-slate-400 font-mono truncate">{ev.text}</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => remove.mutate(ev.id)}
                  className="px-2 py-1 rounded text-xs font-mono text-red-400 hover:bg-red-500/10 shrink-0"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </StatePanel>
    </div>
  );
}
