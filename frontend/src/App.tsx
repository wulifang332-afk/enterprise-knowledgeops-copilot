import { Route, Routes } from "react-router-dom";

import { ApplicationShell } from "./components/ApplicationShell";
import { EvaluationCenterPage } from "./pages/EvaluationCenterPage";
import { GovernanceCenterPage } from "./pages/GovernanceCenterPage";
import { GraphExplorerPage } from "./pages/GraphExplorerPage";
import { HomePage } from "./pages/HomePage";
import { KnowledgeWorkspacePage } from "./pages/KnowledgeWorkspacePage";
import { QueryPlannerPage } from "./pages/QueryPlannerPage";
import { SearchCitationsPage } from "./pages/SearchCitationsPage";

export default function App() {
  return (
    <ApplicationShell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/workspace" element={<KnowledgeWorkspacePage />} />
        <Route path="/search" element={<SearchCitationsPage />} />
        <Route path="/graph" element={<GraphExplorerPage />} />
        <Route path="/query" element={<QueryPlannerPage />} />
        <Route path="/evaluation" element={<EvaluationCenterPage />} />
        <Route path="/governance" element={<GovernanceCenterPage />} />
      </Routes>
    </ApplicationShell>
  );
}
