import { useState, useEffect, useRef, useCallback } from "react";

export interface SessionData {
  score: number;
  simSwap: boolean;
  frozen: boolean;
  history: { time: number; score: number }[];
}

// Simulated score decay for demo (no real backend needed)
const simulatedScores = [91, 85, 80, 74, 68, 58, 52, 44, 38, 27];

export function useSessionPolling(sessionId: string) {
  const [data, setData] = useState<SessionData>({
    score: 91,
    simSwap: false,
    frozen: false,
    history: [{ time: 0, score: 91 }],
  });

  const tickRef = useRef(0);
  const frozenRef = useRef(false);

  useEffect(() => {
    const interval = setInterval(async () => {
      if (frozenRef.current) return;

      // Try real API first
      try {
        const res = await fetch(`http://localhost:8000/score/${sessionId}`, { signal: AbortSignal.timeout(1000) });
        if (res.ok) {
          const json = await res.json();
          const newScore = json.score ?? 91;
          const simSwap = json.simSwap ?? false;
          const frozen = json.frozen ?? false;
          frozenRef.current = frozen;
          setData((prev) => ({
            score: newScore,
            simSwap,
            frozen,
            history: [...prev.history, { time: prev.history.length * 3, score: newScore }].slice(-20),
          }));
          return;
        }
      } catch {
        // API not available — use simulation
      }

      tickRef.current += 1;
      const idx = Math.min(tickRef.current, simulatedScores.length - 1);
      const newScore = simulatedScores[idx];
      const simSwap = idx >= 8;
      const frozen = idx >= simulatedScores.length - 1;
      frozenRef.current = frozen;

      setData((prev) => ({
        score: newScore,
        simSwap,
        frozen,
        history: [...prev.history, { time: prev.history.length * 3, score: newScore }].slice(-20),
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, [sessionId]);

  return data;
}
