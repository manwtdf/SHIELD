import { useState, useEffect, useRef } from "react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export interface SessionData {
  score: number;
  riskLevel: string;
  action: string;
  topAnomalies: string[];
  frozen: boolean;
  history: { time: number; score: number }[];
}

export function useSessionPolling(sessionId: string) {
  const [data, setData] = useState<SessionData>({
    score: 91,
    riskLevel: "LOW",
    action: "ALLOW",
    topAnomalies: [],
    frozen: false,
    history: [{ time: 0, score: 91 }],
  });

  const frozenRef = useRef(false);

  useEffect(() => {
    if (!sessionId) return;
    
    const interval = setInterval(async () => {
      if (frozenRef.current) return;

      try {
        const res = await fetch(`${BACKEND_URL}/score/${sessionId}`, { signal: AbortSignal.timeout(1000) });
        if (res.ok) {
          const json = await res.json();
          const newScore = json.score ?? 91;
          const riskLevel = json.risk_level ?? "LOW";
          const action = json.action ?? "ALLOW";
          const topAnomalies = json.top_anomalies ?? [];
          const frozen = json.risk_level === "CRITICAL" || json.action === "BLOCK_AND_FREEZE";
          
          frozenRef.current = frozen;
          setData((prev) => ({
            score: newScore,
            riskLevel,
            action,
            topAnomalies,
            frozen,
            history: [...prev.history, { time: prev.history.length * 3, score: newScore }].slice(-20),
          }));
        }
      } catch {
        console.error("Score poll failed");
      }

    }, 2000);

    return () => clearInterval(interval);
  }, [sessionId]);

  return data;
}
