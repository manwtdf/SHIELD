import ShieldSidebar from "@/components/dashboard/ShieldSidebar";

const Sessions = () => (
  <div className="flex min-h-screen w-full bg-background">
    <ShieldSidebar />
    <main className="flex-1 p-6">
      <h1 className="text-xl font-bold mb-1">Sessions</h1>
      <p className="text-sm text-shield-muted mb-6">Browse and analyze user sessions</p>
      <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-accent/50">
              <th className="text-left p-3 font-medium text-shield-muted">Session ID</th>
              <th className="text-left p-3 font-medium text-shield-muted">User</th>
              <th className="text-left p-3 font-medium text-shield-muted">Score</th>
              <th className="text-left p-3 font-medium text-shield-muted">Risk</th>
              <th className="text-left p-3 font-medium text-shield-muted">Duration</th>
              <th className="text-left p-3 font-medium text-shield-muted">Status</th>
            </tr>
          </thead>
          <tbody>
            {[
              { id: "sess-0x8a3f", user: "John Kumar", score: 27, risk: "CRITICAL", duration: "24s", status: "Frozen" },
              { id: "sess-0x7b12", user: "Maria Santos", score: 88, risk: "LOW", duration: "3m 12s", status: "Completed" },
              { id: "sess-0x6c45", user: "Alex Chen", score: 52, risk: "MEDIUM", duration: "1m 45s", status: "Step-Up Auth" },
              { id: "sess-0x5d78", user: "Sarah Johnson", score: 94, risk: "LOW", duration: "5m 03s", status: "Completed" },
              { id: "sess-0x4e9b", user: "Omar Patel", score: 38, risk: "HIGH", duration: "32s", status: "Blocked" },
            ].map((s) => (
              <tr key={s.id} className="border-b border-border last:border-0 hover:bg-accent/30 transition-colors">
                <td className="p-3 font-mono text-xs">{s.id}</td>
                <td className="p-3">{s.user}</td>
                <td className="p-3 font-mono font-medium" style={{ color: s.score >= 70 ? "#22C55E" : s.score >= 45 ? "#F59E0B" : "#EF4444" }}>{s.score}</td>
                <td className="p-3">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    s.risk === "LOW" ? "bg-shield-safe/10 text-shield-safe" :
                    s.risk === "MEDIUM" ? "bg-shield-warning/10 text-shield-warning" :
                    s.risk === "HIGH" ? "bg-orange-100 text-orange-600" :
                    "bg-shield-critical/10 text-shield-critical"
                  }`}>{s.risk}</span>
                </td>
                <td className="p-3 font-mono text-xs text-shield-muted">{s.duration}</td>
                <td className="p-3 text-xs text-shield-muted">{s.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  </div>
);

export default Sessions;
