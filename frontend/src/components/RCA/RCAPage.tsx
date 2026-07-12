import { useState } from "react";
import { useRcaReports } from "@/api/client";
import { generateRca } from "@/api/llm";
import { FileText, Lightbulb, Clock, Sparkles, Loader2 } from "lucide-react";

export function RCAPage() {
  const { data: reports, isLoading } = useRcaReports();
  const [incidentId, setIncidentId] = useState("");
  const [generating, setGenerating] = useState(false);
  const [rcaResult, setRcaResult] = useState<string | null>(null);
  const [rcaError, setRcaError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!incidentId.trim()) return;
    setGenerating(true);
    setRcaResult(null);
    setRcaError(null);
    try {
      const data = await generateRca(incidentId.trim());
      setRcaResult(data.llm_rca);
    } catch (err) {
      setRcaError(err instanceof Error ? err.message : "Failed to generate RCA");
    } finally {
      setGenerating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-slate-400">Loading RCA reports...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">
          Root Cause Analysis
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Automated RCA reports correlating metrics, logs, and traces
        </p>
      </div>

      {/* LLM RCA Generator */}
      <div className="glass rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-5 h-5 text-brand-400" />
          <h2 className="text-sm font-medium text-white">Generate LLM-Powered RCA</h2>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Enter an incident ID to generate an AI-powered root cause analysis
        </p>
        <div className="flex gap-3">
          <input
            type="text"
            value={incidentId}
            onChange={(e) => setIncidentId(e.target.value)}
            placeholder="Incident ID (UUID)"
            className="flex-1 px-3 py-2 rounded-lg bg-surface-800 border border-slate-700/50 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50"
          />
          <button
            onClick={handleGenerate}
            disabled={generating || !incidentId.trim()}
            className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:bg-slate-700 text-white text-sm font-medium transition-colors flex items-center gap-2"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            Generate
          </button>
        </div>
        {generating && (
          <div className="mt-3 flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyzing incident with AI...
          </div>
        )}
        {rcaError && (
          <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-sm text-red-400">{rcaError}</p>
          </div>
        )}
        {rcaResult && (
          <div className="mt-3 p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <p className="text-xs font-medium text-brand-400 mb-2">AI Analysis</p>
            <div className="text-sm text-slate-300 whitespace-pre-wrap">
              {rcaResult}
            </div>
          </div>
        )}
      </div>

      {/* Existing RCA Reports */}
      {!reports || reports.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <Lightbulb className="w-12 h-12 text-amber-400 mx-auto mb-3" />
          <p className="text-slate-400">No RCA reports generated yet</p>
          <p className="text-xs text-slate-500 mt-2">
            RCA reports are automatically generated when incidents are resolved
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((rca) => (
            <div key={rca.id} className="glass rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-brand-400" />
                  <h3 className="text-sm font-medium text-white">
                    RCA Report
                  </h3>
                </div>
                <span className="text-xs text-slate-500">
                  <Clock className="w-3 h-3 inline mr-1" />
                  {new Date(rca.created_at).toLocaleDateString()}
                </span>
              </div>

              {rca.summary && (
                <p className="text-sm text-slate-300 mb-3">{rca.summary}</p>
              )}

              {rca.root_cause && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 mb-3">
                  <p className="text-xs font-medium text-red-400 mb-1">
                    Root Cause
                  </p>
                  <p className="text-sm text-slate-300">{rca.root_cause}</p>
                </div>
              )}

              {rca.recommendations && rca.recommendations.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-brand-400 mb-2">
                    Recommendations
                  </p>
                  <ul className="space-y-1">
                    {rca.recommendations.map((rec, i) => (
                      <li
                        key={i}
                        className="text-sm text-slate-400 flex items-start gap-2"
                      >
                        <span className="text-brand-400 mt-0.5">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
