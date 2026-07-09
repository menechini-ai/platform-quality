import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout/Layout";
import { DashboardPage } from "@/components/Dashboard/DashboardPage";
import { IncidentsPage } from "@/components/Incidents/IncidentsPage";
import { IncidentDetailPage } from "@/components/Incidents/IncidentDetailPage";
import { RCAPage } from "@/components/RCA/RCAPage";
import { HealthPage } from "@/components/Health/HealthPage";
import { SelfHealingPage } from "@/components/SelfHealing/SelfHealingPage";
import { MaturityPage } from "@/components/Maturity/MaturityPage";
import { ReportsPage } from "@/components/Reports/ReportsPage";
import { MonitorsPage } from "@/components/Monitors/MonitorsPage";
import { LogsPage } from "@/components/Logs/LogsPage";
import { MetricsPage } from "@/components/Metrics/MetricsPage";
import { SlosPage } from "@/components/Slos/SlosPage";
import { ErrorTrackingPage } from "@/components/ErrorTracking/ErrorTrackingPage";
import { SyntheticsPage } from "@/components/Synthetics/SyntheticsPage";
import { KBSearchPage } from "@/components/KB/KBSearchPage";
import { AgentPipelinePage } from "@/components/Agents/AgentPipelinePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/incidents/:id" element={<IncidentDetailPage />} />
          <Route path="/monitors" element={<MonitorsPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/metrics" element={<MetricsPage />} />
          <Route path="/slos" element={<SlosPage />} />
          <Route path="/error-tracking" element={<ErrorTrackingPage />} />
          <Route path="/synthetics" element={<SyntheticsPage />} />
          <Route path="/rca" element={<RCAPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="/self-healing" element={<SelfHealingPage />} />
          <Route path="/maturity" element={<MaturityPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/kb" element={<KBSearchPage />} />
          <Route path="/agents" element={<AgentPipelinePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
