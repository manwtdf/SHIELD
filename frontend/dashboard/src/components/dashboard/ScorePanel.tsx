import { motion, AnimatePresence } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { SessionData } from "@/hooks/useSessionPolling";

function getScoreColor(score: number) {
  if (score >= 70) return "hsl(142, 71%, 45%)";
  if (score >= 45) return "hsl(38, 92%, 50%)";
  return "hsl(0, 84%, 60%)";
}

function getRiskLevel(score: number) {
  if (score >= 70) return "LOW";
  if (score >= 45) return "MEDIUM";
  if (score >= 30) return "HIGH";
  return "CRITICAL";
}

function getAction(score: number) {
  if (score >= 70) return "ALLOW";
  if (score >= 45) return "STEP-UP AUTH";
  if (score >= 30) return "REVIEW";
  return "BLOCK + FREEZE";
}

const riskBadgeColors: Record<string, string> = {
  LOW: "bg-shield-safe/10 text-shield-safe",
  MEDIUM: "bg-shield-warning/10 text-shield-warning",
  HIGH: "bg-orange-100 text-orange-600",
  CRITICAL: "bg-shield-critical/10 text-shield-critical",
};

interface Props {
  data: SessionData;
  frozen: boolean;
}

const ScorePanel = ({ data, frozen }: Props) => {
  const score = data.score;
  const color = getScoreColor(score);
  const risk = getRiskLevel(score);
  const action = getAction(score);

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-6 flex-1 min-w-0 relative overflow-hidden">
      {frozen && (
        <div className="absolute inset-0 bg-shield-critical/5 z-10 flex items-center justify-center pointer-events-none">
          <span className="text-shield-critical font-bold text-lg tracking-widest opacity-30 rotate-[-15deg]">
            FROZEN
          </span>
        </div>
      )}

      {/* Score */}
      <div className="text-center mb-6">
        <div className="text-[10px] font-bold tracking-[0.2em] text-shield-muted uppercase mb-1">
          Confidence Score
        </div>
        <motion.div
          className="font-mono font-medium leading-none"
          style={{ fontSize: 80, color }}
          key={score}
          initial={{ scale: 1.1, opacity: 0.5 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
        >
          {score}
        </motion.div>
      </div>

      {/* Chart */}
      <div className="h-48 -mx-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.history} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(214, 32%, 91%)" />
            <XAxis
              dataKey="time"
              tickFormatter={(v) => `${v}s`}
              tick={{ fontSize: 11, fill: "hsl(215, 17%, 46%)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: "hsl(215, 17%, 46%)" }}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid hsl(214, 32%, 91%)",
                fontSize: 12,
              }}
            />
            <ReferenceLine
              y={45}
              stroke="hsl(38, 92%, 50%)"
              strokeDasharray="6 4"
              label={{ value: "Step-Up Auth", position: "right", fontSize: 10, fill: "hsl(38, 92%, 50%)" }}
            />
            <ReferenceLine
              y={30}
              stroke="hsl(0, 84%, 60%)"
              strokeDasharray="6 4"
              label={{ value: "Block", position: "right", fontSize: 10, fill: "hsl(0, 84%, 60%)" }}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke={color}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive
              animationDuration={800}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Badges */}
      <div className="flex gap-3 mt-4">
        <span className={`px-3 py-1.5 rounded-lg text-xs font-bold ${riskBadgeColors[risk]}`}>
          RISK LEVEL: {risk}
        </span>
        <span className={`px-3 py-1.5 rounded-lg text-xs font-bold ${
          score < 30 ? "bg-shield-critical/10 text-shield-critical" : 
          score < 45 ? "bg-shield-warning/10 text-shield-warning" : 
          "bg-shield-safe/10 text-shield-safe"
        }`}>
          ACTION: {action}
        </span>
      </div>
    </div>
  );
};

export default ScorePanel;
