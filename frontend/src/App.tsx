import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout/Layout";
import { DashboardPage } from "@/components/Dashboard/DashboardPage";
import { IncidentsPage } from "@/components/Incidents/IncidentsPage";
import { IncidentDetailPage } from "@/components/Incidents/IncidentDetailPage";
import { RCAPage } from "@/components/RCA/RCAPage";
import { HealthPage } from "@/components/Health/HealthPage";
import { SelfHealingPage } from "@/components/SelfHealing/SelfHealingPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/incidents/:id" element={<IncidentDetailPage />} />
          <Route path="/rca" element={<RCAPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="/self-healing" element={<SelfHealingPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
