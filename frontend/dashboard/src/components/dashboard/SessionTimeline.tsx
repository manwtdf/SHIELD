import { useState } from "react";
import { Lock } from "lucide-react";

const nodes = [
  { label: "Login", score: 91, time: "0s", anomalies: ["Logged in from known IP"] },
  { label: "Typing", score: 74, time: "6s", anomalies: ["Inter-key delay +80%", "Hold time deviation"] },
  { label: "Navigation", score: 58, time: "12s", anomalies: ["Direct to /transfer", "Skipped dashboard"] },
  { label: "Device", score: 44, time: "18s", anomalies: ["Unknown fingerprint", "New browser agent"] },
  { label: "SIM Fused", score: 27, time: "24s", anomalies: ["SIM swap detected", "Account frozen"], locked: true },
];

function getNodeColor(score: number) {
  if (score >= 70) return "#22C55E";
  if (score >= 45) return "#F59E0B";
  return "#EF4444";
}

const SessionTimeline = () => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const nodeSpacing = 160;
  const svgWidth = (nodes.length - 1) * nodeSpacing + 80;

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-5 flex-1">
      <h3 className="font-semibold text-sm mb-4">Session Timeline</h3>
      <div className="overflow-x-auto">
        <svg width={svgWidth} height={140} className="block mx-auto">
          <defs>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#22C55E" />
              <stop offset="50%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#EF4444" />
            </linearGradient>
          </defs>

          {/* Connecting line */}
          <line
            x1={40}
            y1={50}
            x2={40 + (nodes.length - 1) * nodeSpacing}
            y2={50}
            stroke="url(#lineGrad)"
            strokeWidth={3}
            strokeLinecap="round"
          />

          {nodes.map((node, i) => {
            const cx = 40 + i * nodeSpacing;
            const cy = 50;
            const color = getNodeColor(node.score);
            const isLast = node.locked;

            return (
              <g
                key={i}
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
                className="cursor-pointer"
              >
                {/* Outer ring for last node */}
                {isLast && (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={22}
                    fill="none"
                    stroke={color}
                    strokeWidth={2}
                    opacity={0.4}
                    className="animate-pulse-red"
                  />
                )}

                {/* Node circle */}
                <circle cx={cx} cy={cy} r={16} fill={color} opacity={0.15} />
                <circle cx={cx} cy={cy} r={12} fill={color} />

                {/* Score text */}
                <text
                  x={cx}
                  y={cy + 4}
                  textAnchor="middle"
                  fill="white"
                  fontSize={10}
                  fontFamily="DM Mono"
                  fontWeight={500}
                >
                  {node.score}
                </text>

                {/* Lock icon for last */}
                {isLast && (
                  <text x={cx + 18} y={cy + 4} fontSize={12}>
                    🔒
                  </text>
                )}

                {/* Label */}
                <text
                  x={cx}
                  y={cy + 35}
                  textAnchor="middle"
                  fill="hsl(215, 17%, 46%)"
                  fontSize={11}
                  fontFamily="Instrument Sans"
                >
                  {node.label}
                </text>

                {/* Time */}
                <text
                  x={cx}
                  y={cy + 50}
                  textAnchor="middle"
                  fill="hsl(215, 17%, 46%)"
                  fontSize={10}
                  fontFamily="DM Mono"
                  opacity={0.7}
                >
                  {node.time}
                </text>

                {/* Tooltip */}
                {hoveredIdx === i && (
                  <foreignObject x={cx - 90} y={cy - 90} width={180} height={75}>
                    <div className="bg-foreground text-primary-foreground rounded-lg p-2.5 text-xs shadow-lg">
                      <div className="font-bold mb-1">{node.label} — Score: {node.score}</div>
                      {node.anomalies.map((a, j) => (
                        <div key={j} className="opacity-80">• {a}</div>
                      ))}
                    </div>
                  </foreignObject>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};

export default SessionTimeline;
