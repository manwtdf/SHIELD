import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { MOCK_FEATURES } from './types';

interface FeatureInspectorProps {
  visible: boolean;
}

export default function FeatureInspector({ visible }: FeatureInspectorProps) {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);

  if (!visible) return null;

  const sorted = [...MOCK_FEATURES].sort((a, b) => Math.abs(b.zScore) - Math.abs(a.zScore));
  const displayed = showAll ? sorted : sorted.slice(0, 10);

  return (
    <div className="border-t border-shield-border bg-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-3 flex items-center justify-between hover:bg-secondary/30 transition-colors"
      >
        <h3 className="font-mono text-xs tracking-[0.2em] text-shield-green uppercase">
          Feature Inspector
        </h3>
        {expanded ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronUp className="w-4 h-4 text-muted-foreground" />}
      </button>
      {expanded && (
        <div className="px-6 pb-4 overflow-auto max-h-[400px]">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-foreground font-mono border-b border-shield-border">
                <th className="text-left p-2">Feature Name</th>
                <th className="text-right p-2">User Baseline</th>
                <th className="text-right p-2">This Session</th>
                <th className="text-right p-2">Z-Score</th>
                <th className="text-center p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((f) => {
                const absZ = Math.abs(f.zScore);
                const rowBg = absZ > 3.0
                  ? 'bg-[rgba(239,68,68,0.15)]'
                  : absZ > 2.0
                  ? 'bg-[rgba(245,158,11,0.10)]'
                  : '';
                return (
                  <tr key={f.name} className={`${rowBg} border-b border-shield-border/30`}>
                    <td className="p-2 font-mono text-foreground">{f.name}</td>
                    <td className="p-2 text-right font-mono text-muted-foreground">{f.baseline}</td>
                    <td className="p-2 text-right font-mono text-foreground">{f.session}</td>
                    <td className="p-2 text-right">
                      <span className={`px-1.5 py-0.5 rounded font-mono ${
                        f.flagged ? 'bg-shield-red/20 text-shield-red' : 'bg-shield-green/20 text-shield-green'
                      }`}>
                        {f.zScore.toFixed(1)}
                      </span>
                    </td>
                    <td className="p-2 text-center">
                      {f.flagged ? '🔴 FLAGGED' : '🟢 NORMAL'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <button
            onClick={() => setShowAll(!showAll)}
            className="mt-2 text-xs text-shield-green hover:underline font-mono"
          >
            {showAll ? 'Show top 10' : `Show all ${MOCK_FEATURES.length}`}
          </button>
        </div>
      )}
    </div>
  );
}
