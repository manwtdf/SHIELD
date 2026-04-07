import { Check, X, Zap, Monitor, Smartphone, Laptop } from "lucide-react";
import type { SessionData } from "@/hooks/useSessionPolling";

const riskColors: Record<string, string> = {
  LOW: "bg-shield-safe/10 text-shield-safe border-shield-safe/30",
  MEDIUM: "bg-shield-warning/10 text-shield-warning border-shield-warning/30",
  HIGH: "bg-orange-100 text-orange-600 border-orange-300",
  CRITICAL: "bg-shield-critical/10 text-shield-critical border-shield-critical/30 animate-pulse-red",
};

function getRiskLevel(score: number) {
  if (score >= 70) return "LOW";
  if (score >= 45) return "MEDIUM";
  if (score >= 30) return "HIGH";
  return "CRITICAL";
}

interface Props {
  data: SessionData;
}

const UserProfilePanel = ({ data }: Props) => {
  const risk = getRiskLevel(data.score);
  const simSwap = data.simSwap;

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-5 space-y-4 w-[280px] shrink-0">
      {/* Avatar + Name */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-foreground text-primary-foreground flex items-center justify-center font-bold text-lg font-mono">
          JK
        </div>
        <div>
          <div className="font-semibold text-sm">John Kumar</div>
          <div className="text-xs text-shield-muted font-mono">Account ****4521</div>
        </div>
      </div>

      {/* Risk badge */}
      <div className={`inline-flex px-3 py-1 rounded-full text-xs font-bold border ${riskColors[risk]}`}>
        {risk} RISK
      </div>

      {/* Info rows */}
      <div className="space-y-2.5 text-sm">
        <div className="flex justify-between items-center">
          <span className="text-shield-muted">Enrolled</span>
          <Check className="w-4 h-4 text-shield-safe" />
        </div>
        <div className="flex justify-between items-center">
          <span className="text-shield-muted">Sessions</span>
          <span className="font-mono font-medium">10</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-shield-muted">Baseline Score</span>
          <span className="font-mono font-medium">91</span>
        </div>
      </div>

      <div className="border-t border-border" />

      {/* Devices */}
      <div className="space-y-2.5 text-sm">
        <div className="flex justify-between items-center">
          <span className="text-shield-muted">Known Devices</span>
          <div className="flex gap-1.5 text-shield-muted">
            <Monitor className="w-4 h-4" />
            <Smartphone className="w-4 h-4" />
            <Laptop className="w-4 h-4" />
          </div>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-shield-muted">Current Device</span>
          {simSwap ? (
            <span className="flex items-center gap-1 text-xs font-bold text-shield-critical bg-shield-critical/10 px-2 py-0.5 rounded-full">
              UNKNOWN <X className="w-3 h-3" />
            </span>
          ) : (
            <span className="text-xs text-shield-safe font-medium">Known ✓</span>
          )}
        </div>
        <div className="flex justify-between items-center">
          <span className="text-shield-muted">SIM Status</span>
          {simSwap ? (
            <span className="flex items-center gap-1 text-xs font-bold text-shield-critical bg-shield-critical/10 px-2 py-0.5 rounded-full">
              <Zap className="w-3 h-3" /> SWAP ACTIVE
            </span>
          ) : (
            <span className="text-xs text-shield-safe font-medium">Normal</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserProfilePanel;
