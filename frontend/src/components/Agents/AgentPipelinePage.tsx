import { useState, useCallback, useRef } from "react";
import { Bot, Send, Loader2, AlertTriangle, CheckCircle } from "lucide-react";
import { analyzeIncident, streamAnalysis } from "@/api/agents";

interface StreamEvent {
  node: string;
  output: string;
}

export function AgentPipelinePage() {
  const [incidentId, setIncidentId] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [result, setResult] = useState<{ analysis: string; recommendation: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const handleRun = useCallback(async () => {
    if (!incidentId.trim() || !description.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setEvents([]);

    try {
      const data = await analyzeIncident(incidentId.trim(), description.trim());
      setResult({
        analysis: data.analysis || "",
        recommendation: data.recommendation || "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, [incidentId, description]);

  const handleStream = useCallback(() => {
    if (!incidentId.trim() || !description.trim()) return;
    setStreaming(true);
    setError(null);
    setResult(null);
    setEvents([]);

    controllerRef.current = streamAnalysis(
      incidentId.trim(),
      description.trim(),
      (node, output) => {
        setEvents((prev) => [...prev, { node, output }]);
      },
      () => {
        setStreaming(false);
      },
      (err) => {
        setError(err.message);
        setStreaming(false);
      },
    );
  }, [incidentId, description]);

  const handleStop = useCallback(() => {
    controllerRef.current?.abort();
    setStreaming(false);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Agent Pipeline</h1>
        <p className="text-sm text-slate-400 mt-1">
          Multi-step AI agent pipeline: triage &rarr; analysis &rarr; recommendation
        </p>
      </div>

      {/* Input Form */}
      <div className="glass rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-brand-400" />
          <h2 className="text-sm font-medium text-white">Run Analysis</h2>
        </div>

        <div>
          <label className="block text-xs text-slate-500 mb-1">Incident ID</label>
          <input
            type="text"
            value={incidentId}
            onChange={(e) => setIncidentId(e.target.value)}
            placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
            className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-slate-700/50 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50"
          />
        </div>

        <div>
          <label className="block text-xs text-slate-500 mb-1">Incident Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the incident in detail..."
            rows={3}
            className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-slate-700/50 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50 resize-none"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleRun}
            disabled={loading || streaming || !incidentId.trim() || !description.trim()}
            className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:bg-slate-700 text-white text-sm font-medium transition-colors flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            Run Full Analysis
          </button>
          <button
            onClick={streaming ? handleStop : handleStream}
            disabled={loading || !incidentId.trim() || !description.trim()}
            className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white text-sm font-medium transition-colors flex items-center gap-2"
          >
            {streaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Bot className="w-4 h-4" />
            )}
            {streaming ? "Stop Stream" : "Stream Analysis"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Streaming Events */}
      {events.length > 0 && (
        <div className="glass rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-medium text-white">Pipeline Execution</h3>
          <div className="space-y-2">
            {events.map((evt, i) => (
              <div key={i} className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-brand-400">
                    {evt.node}
                  </span>
                </div>
                <p className="text-sm text-slate-300">{evt.output}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Full Analysis Result */}
      {result && (
        <div className="space-y-4">
          <div className="glass rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <h3 className="text-sm font-medium text-white">Analysis</h3>
            </div>
            <p className="text-sm text-slate-300 whitespace-pre-wrap">
              {result.analysis || "No analysis generated"}
            </p>
          </div>

          {result.recommendation && (
            <div className="glass rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle className="w-5 h-5 text-brand-400" />
                <h3 className="text-sm font-medium text-white">Recommendation</h3>
              </div>
              <p className="text-sm text-slate-300 whitespace-pre-wrap">
                {result.recommendation}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
