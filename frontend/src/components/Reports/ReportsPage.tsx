import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { FileText, Calendar, Tag, Plus, Loader2 } from "lucide-react";
import { useState } from "react";

interface Report {
  id: string;
  report_type: string;
  title: string;
  content: string;
  tags: string[];
  created_at: string;
}

const reportTypeIcons: Record<string, string> = {
  executive: "📊",
  monthly: "📅",
  team_health: "🏥",
  postmortem: "🔍",
  investigation: "🔬",
};

const typeColors: Record<string, string> = {
  executive: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  monthly: "bg-green-500/10 text-green-400 border-green-500/20",
  team_health: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  postmortem: "bg-red-500/10 text-red-400 border-red-500/20",
  investigation: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
};

function useReports() {
  return useQuery<Report[]>({
    queryKey: ["reports"],
    queryFn: () => api("/reports"),
  });
}

export function ReportsPage() {
  const { data: reports, isLoading } = useReports();
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createType, setCreateType] = useState("executive");
  const [createTitle, setCreateTitle] = useState("");
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: { report_type: string; title: string }) =>
      api("/reports", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      setShowCreate(false);
      setCreateTitle("");
    },
  });

  if (selectedReport) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setSelectedReport(null)}
          className="text-sm text-blue-400 hover:text-blue-300"
        >
          ← Back to Reports
        </button>
        <div className="bgmocha-mantle rounded-lg border bordermocha-crust p-6">
          <div className="flex items-center gap-3 mb-4">
            <span>{reportTypeIcons[selectedReport.report_type] || "📄"}</span>
            <div>
              <h2 className="text-xl font-semibold text-white">
                {selectedReport.title}
              </h2>
              <p className="text-sm text-gray-400">
                {selectedReport.report_type.replace("_", " ")}
              </p>
            </div>
          </div>
          <div className="prose prose-invert max-w-none text-sm text-gray-300 whitespace-pre-wrap font-mono bgmocha-base rounded-lg p-4">
            {selectedReport.content}
          </div>
          {selectedReport.tags && selectedReport.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {selectedReport.tags.map((tag: string) => (
                <span
                  key={tag}
                  className="text-xs px-2 py-1 rounded bgmocha-crust text-gray-400"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
          <p className="text-xs text-gray-500 mt-4">
            {new Date(selectedReport.created_at).toLocaleString()}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-white">Reports</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Report
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bgmocha-mantle rounded-lg border bordermocha-crust p-4 space-y-3">
          <select
            value={createType}
            onChange={(e) => setCreateType(e.target.value)}
            className="w-full bgmocha-crust text-white px-3 py-2 rounded border bordermocha-overlay text-sm"
          >
            <option value="executive">Executive Summary</option>
            <option value="monthly">Monthly Report</option>
            <option value="team_health">Team Health</option>
            <option value="investigation">Investigation</option>
          </select>
          <input
            type="text"
            placeholder="Report title..."
            value={createTitle}
            onChange={(e) => setCreateTitle(e.target.value)}
            className="w-full bgmocha-crust text-white px-3 py-2 rounded border bordermocha-overlay text-sm placeholder-gray-500"
          />
          <button
            onClick={() => createMutation.mutate({ report_type: createType, title: createTitle })}
            disabled={!createTitle || createMutation.isPending}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {createMutation.isPending ? "Generating..." : "Generate Report"}
          </button>
        </div>
      )}

      {/* Report list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
        </div>
      ) : reports && reports.length > 0 ? (
        <div className="space-y-3">
          {reports.map((report) => (
            <div
              key={report.id}
              onClick={() => setSelectedReport(report)}
              className="bgmocha-mantle rounded-lg border bordermocha-crust p-4 hover:border-blue-500/40 cursor-pointer transition-colors"
            >
              <div className="flex items-start gap-3">
                <span className="text-lg mt-1">
                  {reportTypeIcons[report.report_type] || "📄"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-white font-medium truncate">{report.title}</h3>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full border capitalize ${
                        typeColors[report.report_type] ||
                        "bg-gray-500/10 text-gray-400 border-gray-500/20"
                      }`}
                    >
                      {report.report_type.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 line-clamp-2">
                    {report.content.slice(0, 200)}...
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(report.created_at).toLocaleDateString()}
                    </span>
                    {report.tags && report.tags.length > 0 && (
                      <span className="flex items-center gap-1">
                        <Tag className="w-3 h-3" />
                        {report.tags.join(", ")}
                      </span>
                    )}
                  </div>
                </div>
                <FileText className="w-5 h-5 text-gray-500 shrink-0 mt-1" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No reports yet</p>
          <p className="text-sm mt-1">Create one or generate a postmortem from an incident</p>
        </div>
      )}
    </div>
  );
}
