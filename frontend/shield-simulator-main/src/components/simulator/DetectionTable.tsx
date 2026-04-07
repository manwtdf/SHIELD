import { motion, AnimatePresence } from 'framer-motion';
import type { ScenarioResult } from './types';

interface DetectionTableProps {
  results: ScenarioResult[];
}

const resultBadge: Record<string, string> = {
  'BLOCKED': 'bg-shield-red/20 text-shield-red border-shield-red/40',
  'STEP-UP': 'bg-shield-amber/20 text-shield-amber border-shield-amber/40',
  'ALLOWED': 'bg-shield-green/20 text-shield-green border-shield-green/40',
  'ALL FROZEN': 'bg-shield-red/30 text-shield-red border-shield-red/50 font-bold',
};

export default function DetectionTable({ results }: DetectionTableProps) {
  return (
    <div className="mt-6">
      <h3 className="font-mono text-xs tracking-[0.2em] text-shield-green mb-3 uppercase flex items-center gap-2">
        Detection Results
      </h3>
      <div className="border border-shield-border rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-secondary/50 text-muted-foreground font-mono text-xs">
              <th className="text-left p-2.5 border-b border-shield-border">Scenario</th>
              <th className="text-center p-2.5 border-b border-shield-border">Score</th>
              <th className="text-center p-2.5 border-b border-shield-border">Detected</th>
              <th className="text-center p-2.5 border-b border-shield-border">Time</th>
              <th className="text-center p-2.5 border-b border-shield-border">Result</th>
              <th className="text-center p-2.5 border-b border-shield-border">Legacy System</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence>
              {results.map((r, i) => (
                <motion.tr
                  key={r.scenarioId}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="border-b border-shield-border/50"
                >
                  <td className="p-2.5 text-foreground">{r.scenarioName}</td>
                  <td className="p-2.5 text-center font-mono text-foreground font-bold">{r.score}</td>
                  <td className="p-2.5 text-center">{r.detected ? '✅' : '❌'}</td>
                  <td className="p-2.5 text-center font-mono text-muted-foreground">{r.time}</td>
                  <td className="p-2.5 text-center">
                    <span className={`px-2 py-0.5 rounded border text-xs font-mono ${resultBadge[r.result] || ''}`}>
                      {r.result}
                    </span>
                  </td>
                  <td className="p-2.5 text-center text-shield-red font-mono text-xs">
                    {r.legacyResult}
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
            {/* Legacy baseline row */}
            <tr className="bg-shield-red/5 border-t border-shield-border">
              <td className="p-2.5 text-muted-foreground italic">Legacy Rule-Based</td>
              <td className="p-2.5 text-center text-muted-foreground">N/A</td>
              <td className="p-2.5 text-center">❌</td>
              <td className="p-2.5 text-center text-muted-foreground">N/A</td>
              <td className="p-2.5 text-center">
                <span className="px-2 py-0.5 rounded border text-xs font-mono bg-shield-red/20 text-shield-red border-shield-red/40">
                  APPROVED ❌
                </span>
              </td>
              <td className="p-2.5 text-center text-shield-red font-mono text-xs">APPROVED ❌</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
