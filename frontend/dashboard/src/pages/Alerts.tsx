import ShieldSidebar from "@/components/dashboard/ShieldSidebar";
import { Bell, Zap, AlertTriangle } from "lucide-react";

const alertsData = [
  { id: 1, severity: "critical", icon: Zap, title: "SIM SWAP ACTIVE", user: "John Kumar", session: "sess-0x8a3f", time: "6 min ago" },
  { id: 2, severity: "critical", icon: Bell, title: "New device fingerprint", user: "John Kumar", session: "sess-0x8a3f", time: "6 min ago" },
  { id: 3, severity: "warning", icon: AlertTriangle, title: "Typing anomaly — +80% delay", user: "John Kumar", session: "sess-0x8a3f", time: "12 min ago" },
  { id: 4, severity: "warning", icon: AlertTriangle, title: "Navigation — direct to transfer", user: "John Kumar", session: "sess-0x8a3f", time: "18 min ago" },
  { id: 5, severity: "warning", icon: AlertTriangle, title: "Unusual login time", user: "Omar Patel", session: "sess-0x4e9b", time: "1h ago" },
  { id: 6, severity: "critical", icon: Zap, title: "Credential stuffing pattern", user: "Omar Patel", session: "sess-0x4e9b", time: "1h ago" },
];

const Alerts = () => (
  <div className="flex min-h-screen w-full bg-background">
    <ShieldSidebar />
    <main className="flex-1 p-6">
      <h1 className="text-xl font-bold mb-1">Alerts</h1>
      <p className="text-sm text-shield-muted mb-6">All triggered alerts across sessions</p>
      <div className="space-y-2 max-w-2xl">
        {alertsData.map((a) => (
          <div key={a.id} className={`flex items-start gap-3 p-4 rounded-xl border ${
            a.severity === "critical" ? "border-shield-critical/30 bg-shield-critical/5" : "border-shield-warning/30 bg-shield-warning/5"
          }`}>
            <a.icon className={`w-4 h-4 mt-0.5 shrink-0 ${a.severity === "critical" ? "text-shield-critical" : "text-shield-warning"}`} />
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm">{a.title}</div>
              <div className="text-xs text-shield-muted mt-0.5">{a.user} · {a.session} · {a.time}</div>
            </div>
          </div>
        ))}
      </div>
    </main>
  </div>
);

export default Alerts;
