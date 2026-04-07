import { motion, AnimatePresence } from "framer-motion";
import { Zap, AlertTriangle, Circle, MessageSquare } from "lucide-react";

const severityStyles: Record<string, string> = {
  critical: "border-shield-critical/30 bg-shield-critical/5",
  warning: "border-shield-warning/30 bg-shield-warning/5",
};

const iconStyles: Record<string, string> = {
  critical: "text-shield-critical",
  warning: "text-shield-warning",
};

interface AlertFeedProps {
  topAnomalies?: string[];
  action?: string;
  riskLevel?: string;
}

const AlertFeed = ({ topAnomalies = [], action, riskLevel }: AlertFeedProps) => {
  const alerts = topAnomalies.map((text, i) => {
    let severity = "warning";
    let icon = AlertTriangle;
    if (text.toUpperCase().includes("SIM SWAP") || riskLevel === "CRITICAL") {
      severity = "critical";
      if (text.toUpperCase().includes("SIM")) icon = Zap;
    }
    return { id: `anomaly-${i}`, severity, icon, text, time: "Just now" };
  });

  const hasCritical = alerts.some((a) => a.severity === "critical");

  const handleSendAlert = async () => {
    try {
      await fetch("http://localhost:8000/alert/send", { method: "POST" });
      console.log("SMS alert sent");
    } catch {
      console.log("Failed to send alert (API unavailable)");
    }
  };

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-5 w-80 shrink-0 flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <h3 className="font-semibold text-sm">Live Alerts</h3>
        {hasCritical && (
          <span className="w-2 h-2 rounded-full bg-shield-critical animate-pulse-dot" />
        )}
      </div>

      {/* Alert cards */}
      <div className="space-y-2 flex-1">
        <AnimatePresence>
          {alerts.map((alert, i) => (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.15 }}
              className={`flex items-start gap-2.5 p-3 rounded-lg border text-sm ${severityStyles[alert.severity]}`}
            >
              <alert.icon className={`w-4 h-4 mt-0.5 shrink-0 ${iconStyles[alert.severity]}`} />
              <div className="min-w-0">
                <div className="font-medium text-foreground">{alert.text}</div>
                <div className="text-xs text-shield-muted mt-0.5">{alert.time}</div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Send SMS */}
      <button
        onClick={handleSendAlert}
        className="mt-4 w-full flex items-center justify-center gap-2 bg-shield-critical text-white font-semibold text-sm py-2.5 rounded-lg hover:opacity-90 transition-opacity"
      >
        <MessageSquare className="w-4 h-4" />
        SEND SMS ALERT
      </button>
    </div>
  );
};

export default AlertFeed;
