import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { MOCK_FEATURES } from './types';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

interface FeatureInspectorProps {
  visible: boolean;
  sessionId?: string;
}

export default function FeatureInspector({ visible, sessionId }: FeatureInspectorProps) {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [realFeatures, setRealFeatures] = useState<any[]>([]);

  useEffect(() => {
    if (visible && sessionId) {
      fetch(`${API_BASE}/features/inspect/${sessionId}`)
        .then(res => res.json())
        .then(data => {
          if (data.features) {
            setRealFeatures(data.features);
          }
        })
        .catch(console.error);
    }
  }, [visible, sessionId]);

  if (!visible) return null;

  const dataset = realFeatures.length > 0 ? realFeatures : MOCK_FEATURES;
  const sorted = [...dataset].sort((a, b) => {
    const zA = a.z_score ?? a.zScore;
    const zB = b.z_score ?? b.zScore;
    return Math.abs(zB) - Math.abs(zA);
  });
  
  const displayed = showAll ? sorted : sorted.slice(0, 10);

  return (
    <div className="border-t border-border bg-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-3 flex items-center justify-between hover:bg-secondary/30 transition-colors"
      >
        <h3 className="font-mono text-xs tracking-[0.2em] text-shield-green uppercase">
          Feature Inspector
        </h3>
        {expanded ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronUp className="w-4 h-4 text-slate-500" />}
      </button>
      {expanded && (
        <div className="px-6 pb-4 overflow-auto max-h-[400px]">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 font-mono border-b border-border">
                <th className="text-left p-2">Feature Name</th>
                <th className="text-right p-2">User Baseline</th>
                <th className="text-right p-2">This Session</th>
                <th className="text-right p-2">Z-Score</th>
                <th className="text-center p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((f) => {
                const zVal = f.z_score ?? f.zScore;
                const absZ = Math.abs(zVal);
                const rowBg = absZ > 3.0
                  ? 'bg-[rgba(239,68,68,0.15)]'
                  : absZ > 2.0
                  ? 'bg-[rgba(245,158,11,0.10)]'
                  : '';
                return (
                  <tr key={f.name} className={`${rowBg} border-b border-border/30`}>
                    <td className="p-2 font-mono text-foreground">{f.name}</td>
                    <td className="p-2 text-right font-mono text-slate-500">{f.baseline}</td>
                    <td className="p-2 text-right font-mono text-foreground">{f.session ?? f.value}</td>
                    <td className="p-2 text-right">
                      <span className={`px-1.5 py-0.5 rounded font-mono ${
                        f.flagged ? 'bg-shield-red/20 text-shield-red' : 'bg-shield-green/20 text-shield-green'
                      }`}>
                        {zVal.toFixed(1)}
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
            {showAll ? 'Show top 10' : `Show all ${dataset.length}`}
          </button>
        </div>
      )}
    </div>
  );
}
