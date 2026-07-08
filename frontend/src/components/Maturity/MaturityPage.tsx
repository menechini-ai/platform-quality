import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { TrendingUp, Target, Lightbulb, ArrowRight } from "lucide-react";
import { useState } from "react";

interface Level {
  level: number;
  name: string;
  focus: string;
  min_score: number;
}

interface Dimension {
  name: string;
  label: string;
  weight: number;
}

interface Gap {
  target_level: number;
  name: string;
  focus: string;
  required_score: number;
  steps: string[];
}

interface Assessment {
  id: string;
  overall_level: number;
  overall_score: number;
  dimensions: Record<string, number>;
  summary: string;
  created_at: string;
}

const levelColors: Record<number, string> = {
  0: "bg-gray-600",
  1: "bg-red-500",
  2: "bg-orange-500",
  3: "bg-yellow-500",
  4: "bg-green-500",
  5: "bg-emerald-400",
};

const levelLabels: Record<number, string> = {
  0: "Foundation",
  1: "Reactive",
  2: "Proactive",
  3: "Managed",
  4: "Optimized",
  5: "Excellence",
};

function useAssessments() {
  return useQuery<Assessment[]>({
    queryKey: ["maturity"],
    queryFn: () => api("/maturity"),
  });
}

function useLatestAssessment() {
  return useQuery<Assessment | null>({
    queryKey: ["maturity", "latest"],
    queryFn: () => api("/maturity/latest"),
  });
}

function useGapAnalysis(current: number, target: number) {
  return useQuery<Gap[]>({
    queryKey: ["maturity", "gap", current, target],
    queryFn: () => api(`/maturity/gap?current=${current}&target=${target}`),
    enabled: target > current,
  });
}

function useLevels() {
  return useQuery<{ levels: Level[]; dimensions: Dimension[] }>({
    queryKey: ["maturity", "levels"],
    queryFn: () => api("/maturity/levels"),
  });
}

export function MaturityPage() {
  const { data: assessments } = useAssessments();
  const { data: latest } = useLatestAssessment();
  const { data: levelsData } = useLevels();
  const [targetLevel, setTargetLevel] = useState(3);
  const { data: customGaps } = useGapAnalysis(latest?.overall_level ?? 0, targetLevel);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight text-white">
        SRE Maturity Assessment
      </h1>

      {/* Current level indicator */}
      {latest && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[#1e1e2e] rounded-lg border border-[#313244] p-6">
            <p className="text-sm text-gray-400 mb-1">Current Level</p>
            <div className="flex items-center gap-3">
              <span
                className={`inline-flex items-center justify-center w-12 h-12 rounded-full text-white font-bold text-lg ${
                  levelColors[latest.overall_level] || "bg-gray-600"
                }`}
              >
                {latest.overall_level}
              </span>
              <div>
                <p className="text-xl font-semibold text-white">
                  {levelLabels[latest.overall_level]}
                </p>
                <p className="text-sm text-gray-400">
                  Score: {latest.overall_score}/100
                </p>
              </div>
            </div>
          </div>

          <div className="bg-[#1e1e2e] rounded-lg border border-[#313244] p-6">
            <p className="text-sm text-gray-400 mb-1">Assessments Run</p>
            <p className="text-2xl font-semibold text-white">
              {assessments?.length ?? 0}
            </p>
          </div>

          <div className="bg-[#1e1e2e] rounded-lg border border-[#313244] p-6">
            <p className="text-sm text-gray-400 mb-1">Last Assessment</p>
            <p className="text-sm text-gray-300">
              {new Date(latest.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      )}

      {/* Dimension scores */}
      {latest && latest.dimensions && Object.keys(latest.dimensions).length > 0 && (
        <div className="bg-[#1e1e2e] rounded-lg border border-[#313244] p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-400" />
            Dimension Scores
          </h2>
          <div className="space-y-3">
            {Object.entries(latest.dimensions).map(([key, score]) => (
              <div key={key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-300">
                    {levelsData?.dimensions.find((d) => d.name === key)?.label || key}
                  </span>
                  <span className="text-gray-400">{score}/100</span>
                </div>
                <div className="h-2 bg-[#313244] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${score}%`,
                      background:
                        score >= 80
                          ? "linear-gradient(90deg, #22c55e, #16a34a)"
                          : score >= 50
                          ? "linear-gradient(90deg, #eab308, #ca8a04)"
                          : "linear-gradient(90deg, #ef4444, #dc2626)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Gap analysis */}
      <div className="bg-[#1e1e2e] rounded-lg border border-[#313244] p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-purple-400" />
          Gap Analysis
        </h2>
        <div className="flex items-center gap-3 mb-4">
          <span className="text-sm text-gray-400">Target Level:</span>
          <select
            value={targetLevel}
            onChange={(e) => setTargetLevel(Number(e.target.value))}
            className="bg-[#313244] text-white px-3 py-1.5 rounded border border-[#45475a] text-sm"
          >
            {[...Array(6).keys()].map((l) => (
              <option key={l} value={l}>
                Level {l} — {levelLabels[l]}
              </option>
            ))}
          </select>
        </div>

        {customGaps && customGaps.length > 0 ? (
          <div className="space-y-4">
            {customGaps.map((gap) => (
              <div
                key={gap.target_level}
                className="border border-[#313244] rounded-lg p-4"
              >
                <h3 className="font-semibold text-white mb-1">
                  Level {gap.target_level}: {gap.name}
                </h3>
                <p className="text-sm text-gray-400 mb-3">{gap.focus}</p>
                <ul className="space-y-1.5">
                  {gap.steps.map((step, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                      <ArrowRight className="w-4 h-4 mt-0.5 text-blue-400 shrink-0" />
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            {latest
              ? "You're at or above the target level! 🎉"
              : "Run an assessment first to see gaps."}
          </p>
        )}
      </div>

      {/* Run assessment button */}
      <button
        onClick={async () => {
          await api("/maturity/assess", { method: "POST" });
          window.location.reload();
        }}
        className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
      >
        Run New Assessment
      </button>

      {/* Levels reference */}
      {levelsData && (
        <div className="bg-[#1e1e2e] rounded-lg border border-[#313244] p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-400" />
            Maturity Levels Reference
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-[#313244]">
                  <th className="text-left py-2 pr-4">Level</th>
                  <th className="text-left py-2 pr-4">Name</th>
                  <th className="text-left py-2">Focus</th>
                </tr>
              </thead>
              <tbody>
                {levelsData.levels.map((lvl) => (
                  <tr key={lvl.level} className="border-b border-[#313244] last:border-0">
                    <td className="py-2 pr-4">
                      <span
                        className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-white text-xs font-bold ${
                          levelColors[lvl.level] || "bg-gray-600"
                        }`}
                      >
                        {lvl.level}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-white font-medium">{lvl.name}</td>
                    <td className="py-2 text-gray-400">{lvl.focus}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
