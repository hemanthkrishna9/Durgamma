import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { LayoutDashboard, Rocket, ListTodo, Users, Activity, DollarSign, ShieldCheck, Code, Package } from "lucide-react";
import HomePage from "./pages/HomePage";
import MissionIntakePage from "./pages/MissionIntakePage";
import MissionDashboard from "./pages/MissionDashboard";
import TaskBoardPage from "./pages/TaskBoardPage";
import AgentMonitorPage from "./pages/AgentMonitorPage";
import ActivityFeedPage from "./pages/ActivityFeedPage";
import CostTrackerPage from "./pages/CostTrackerPage";
import ApprovalsPage from "./pages/ApprovalsPage";
import CodeViewerPage from "./pages/CodeViewerPage";
import DeliveryPage from "./pages/DeliveryPage";
import "./App.css";

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-header">
          <Rocket size={24} />
          <span>Mission Control</span>
        </div>
        <div className="sidebar-links">
          <NavLink to="/" end><LayoutDashboard size={18} /> Home</NavLink>
          <NavLink to="/new"><Rocket size={18} /> New Mission</NavLink>
        </div>
        <div className="sidebar-section">Mission Views</div>
        <div className="sidebar-links">
          <NavLink to="/tasks"><ListTodo size={18} /> Task Board</NavLink>
          <NavLink to="/agents"><Users size={18} /> Agents</NavLink>
          <NavLink to="/activity"><Activity size={18} /> Activity Feed</NavLink>
          <NavLink to="/cost"><DollarSign size={18} /> Cost Tracker</NavLink>
          <NavLink to="/approvals"><ShieldCheck size={18} /> Approvals</NavLink>
          <NavLink to="/code"><Code size={18} /> Code Viewer</NavLink>
          <NavLink to="/delivery"><Package size={18} /> Delivery</NavLink>
        </div>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/new" element={<MissionIntakePage />} />
          <Route path="/mission/:id" element={<MissionDashboard />} />
          <Route path="/tasks" element={<TaskBoardPage />} />
          <Route path="/agents" element={<AgentMonitorPage />} />
          <Route path="/activity" element={<ActivityFeedPage />} />
          <Route path="/cost" element={<CostTrackerPage />} />
          <Route path="/approvals" element={<ApprovalsPage />} />
          <Route path="/code" element={<CodeViewerPage />} />
          <Route path="/delivery" element={<DeliveryPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
