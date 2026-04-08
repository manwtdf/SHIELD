import { useSearchParams } from "react-router-dom";
import ShieldSidebar from "../components/dashboard/ShieldSidebar";
import UserProfilePanel from "../components/dashboard/UserProfilePanel";
import ScorePanel from "../components/dashboard/ScorePanel";
import AlertFeed from "../components/dashboard/AlertFeed";
import AnomalyList from "../components/dashboard/AnomalyList";
import SessionTimeline from "../components/dashboard/SessionTimeline";
import { useSessionPolling } from "../hooks/useSessionPolling";

export const DashboardPage = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session") || localStorage.getItem("shieldSessionId") || "demo-session";
  const data = useSessionPolling(sessionId);

  return (
    <div className="flex min-h-screen w-full bg-background">
      <ShieldSidebar />

      <main className="flex-1 p-6 overflow-auto pb-28">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-bold">Session Analysis</h1>
          <p className="text-sm text-shield-muted">
            Real-time behavioral biometric scoring — Session: <span className="font-mono">{sessionId}</span>
          </p>
        </div>

        {/* Top 3 columns */}
        <div className="flex gap-5 mb-5">
          <UserProfilePanel data={data} />
          <ScorePanel data={data} frozen={data.frozen} />
          <AlertFeed sessionId={sessionId} topAnomalies={data.topAnomalies} action={data.action} riskLevel={data.riskLevel} />
        </div>

        {/* Bottom 2 panels */}
        <div className="flex gap-5">
          <AnomalyList />
          <SessionTimeline />
        </div>
      </main>
    </div>
  );
};

export default DashboardPage;
