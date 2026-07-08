import { useState, useCallback } from "react";
import { Search, BookOpen, Loader2 } from "lucide-react";
import { searchKb, type KbSearchResult } from "@/api/llm";

function ResultCard({ result }: { result: KbSearchResult }) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-sm font-medium text-white">{result.title}</h3>
        <span className="text-xs font-mono text-brand-400 ml-2 shrink-0">
          {Math.round(result.score * 100)}%
        </span>
      </div>
      {result.symptom_pattern && (
        <p className="text-xs text-slate-500 mb-1">
          <span className="text-slate-400">Symptom:</span> {result.symptom_pattern}
        </p>
      )}
      {result.root_cause && (
        <p className="text-sm text-slate-300 mb-2">{result.root_cause}</p>
      )}
      {result.resolution_steps && result.resolution_steps.length > 0 && (
        <div>
          <p className="text-xs font-medium text-brand-400 mb-1">Steps</p>
          <ol className="list-decimal list-inside space-y-0.5">
            {result.resolution_steps.map((step, i) => (
              <li key={i} className="text-xs text-slate-400">
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

export function KBSearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KbSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await searchKb(query.trim());
      setResults(data.results);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Knowledge Base</h1>
        <p className="text-sm text-slate-400 mt-1">
          Semantic search across RCA patterns, runbooks, and incident resolutions
        </p>
      </div>

      {/* Search bar */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search the knowledge base… e.g. database failover during deploy"
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-surface-800 border border-slate-700/50 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50"
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-slate-700 text-white text-sm font-medium transition-colors flex items-center gap-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          Search
        </button>
      </div>

      {/* Results */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-brand-400" />
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="glass rounded-xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-slate-500 mx-auto mb-3" />
          <p className="text-slate-400">No matching entries found</p>
          <p className="text-xs text-slate-500 mt-2">
            Try a different search term or browse all entries
          </p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            Found {results.length} result{results.length !== 1 ? "s" : ""}
          </p>
          {results.map((r) => (
            <ResultCard key={r.id} result={r} />
          ))}
        </div>
      )}
    </div>
  );
}
