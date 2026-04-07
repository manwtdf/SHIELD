import ShieldSidebar from "@/components/dashboard/ShieldSidebar";

const scenarios = [
  { name: "Account Takeover", description: "Detects credential stuffing + device change + SIM swap combination", triggers: 3, lastTriggered: "6 min ago", severity: "critical" },
  { name: "Synthetic Identity", description: "New account with bot-like typing and navigation patterns", triggers: 0, lastTriggered: "Never", severity: "warning" },
  { name: "Insider Fraud", description: "Known user with deviation from baseline behavior >3σ", triggers: 1, lastTriggered: "2 days ago", severity: "warning" },
  { name: "Money Mule", description: "Rapid transfers after unusual login pattern", triggers: 1, lastTriggered: "5 days ago", severity: "critical" },
];

const Scenarios = () => (
  <div className="flex min-h-screen w-full bg-background">
    <ShieldSidebar />
    <main className="flex-1 p-6">
      <h1 className="text-xl font-bold mb-1">Scenarios</h1>
      <p className="text-sm text-shield-muted mb-6">Fraud detection rule scenarios</p>
      <div className="grid gap-4 max-w-3xl">
        {scenarios.map((s) => (
          <div key={s.name} className="bg-card rounded-xl border border-border shadow-sm p-5">
            <div className="flex items-start justify-between mb-2">
              <div className="font-semibold text-sm">{s.name}</div>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                s.severity === "critical" ? "bg-shield-critical/10 text-shield-critical" : "bg-shield-warning/10 text-shield-warning"
              }`}>{s.severity.toUpperCase()}</span>
            </div>
            <div className="text-xs text-shield-muted mb-3">{s.description}</div>
            <div className="flex gap-4 text-xs text-shield-muted">
              <span>Triggers: <span className="font-mono font-medium text-foreground">{s.triggers}</span></span>
              <span>Last: <span className="font-mono">{s.lastTriggered}</span></span>
            </div>
          </div>
        ))}
      </div>
    </main>
  </div>
);

export default Scenarios;
