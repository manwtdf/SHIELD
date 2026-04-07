import { SCENARIOS, type Scenario, type StepStatus } from './types';
import { Check, Zap, RotateCcw } from 'lucide-react';

interface ScenarioSidebarProps {
  activeScenario: number;
  onSelectScenario: (id: number) => void;
  stepStatuses: StepStatus[];
  stepData: { baseline?: number; elapsed?: string; snapshot?: string };
  onRunStep: (step: number) => void;
  onReset: () => void;
}

const strengthColors: Record<string, string> = {
  STRONG: 'bg-shield-green/20 text-shield-green border-shield-green/30',
  MODERATE: 'bg-shield-amber/20 text-shield-amber border-shield-amber/30',
  CONTROL: 'bg-shield-blue/20 text-shield-blue border-shield-blue/30',
};

export default function ScenarioSidebar({
  activeScenario, onSelectScenario, stepStatuses, stepData, onRunStep, onReset,
}: ScenarioSidebarProps) {
  const stepLabels = [
    { label: '1. ENROLL USER', icon: null },
    { label: '2. TRIGGER SIM SWAP', icon: <Zap className="w-3 h-3" /> },
    { label: '3. RUN ATTACK SESSION', icon: null },
    { label: '4. COMPARE LEGACY', icon: null },
  ];

  const getStepExtra = (i: number) => {
    if (stepStatuses[i] !== 'done') {
      if (stepStatuses[i] === 'active') {
        if (i === 1) return <span className="text-shield-amber font-mono text-xs">{stepData.elapsed || '0:00 elapsed'}</span>;
        if (i === 2) return <span className="text-shield-amber font-mono text-xs">{stepData.snapshot || 'Running...'}</span>;
      }
      return null;
    }
    if (i === 0) return <span className="text-shield-green font-mono text-xs">✓ Baseline: {stepData.baseline ?? 91}</span>;
    if (i === 1) return <span className="text-shield-green font-mono text-xs">✓ SIM swapped</span>;
    if (i === 2) return <span className="text-shield-green font-mono text-xs">✓ Complete</span>;
    if (i === 3) return <span className="text-shield-green font-mono text-xs">✓ Compared</span>;
    return null;
  };

  const stepBtnClass = (status: StepStatus) => {
    switch (status) {
      case 'pending': return 'border-border text-muted-foreground cursor-not-allowed opacity-40';
      case 'ready': return 'border-shield-green text-foreground cursor-pointer hover:shadow-[0_0_15px_hsl(153_100%_50%/0.3)]';
      case 'active': return 'border-shield-amber text-foreground cursor-wait animate-[pulse-border_1.5s_ease-in-out_infinite]';
      case 'done': return 'bg-shield-green/20 border-shield-green text-shield-green cursor-default';
    }
  };

  return (
    <aside className="w-[300px] min-w-[300px] bg-card border-r border-shield-border flex flex-col h-full overflow-y-auto">
      <div className="p-4">
        <h3 className="font-mono text-xs tracking-[0.2em] text-shield-green mb-3 uppercase">
          Attack Scenarios
        </h3>
        <div className="space-y-1.5">
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              onClick={() => onSelectScenario(s.id)}
              className={`w-full text-left p-2.5 rounded transition-all border ${
                activeScenario === s.id
                  ? 'border-l-[3px] border-l-shield-green border-t-shield-border border-r-shield-border border-b-shield-border bg-secondary'
                  : 'border-shield-border hover:bg-secondary/50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-muted-foreground">{String(s.id).padStart(2, '0')}</span>
                  <span className="text-sm text-foreground">{s.name}</span>
                </div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${strengthColors[s.strength]}`}>
                  {s.strength}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 border-t border-shield-border flex-1">
        <h3 className="font-mono text-xs tracking-[0.2em] text-shield-green mb-3 uppercase">
          Execution Steps
        </h3>
        <div className="space-y-2">
          {stepLabels.map((step, i) => (
            <button
              key={i}
              onClick={() => stepStatuses[i] === 'ready' && onRunStep(i)}
              disabled={stepStatuses[i] === 'pending' || stepStatuses[i] === 'done'}
              className={`w-full text-left p-2.5 rounded border transition-all font-mono text-xs ${stepBtnClass(stepStatuses[i])}`}
            >
              <div className="flex items-center gap-1.5">
                {stepStatuses[i] === 'done' && <Check className="w-3 h-3" />}
                {step.label}
                {step.icon}
              </div>
              {getStepExtra(i)}
            </button>
          ))}
        </div>
        <button
          onClick={onReset}
          className="mt-4 w-full p-2 rounded border border-shield-red/50 text-shield-red text-xs font-mono hover:bg-shield-red/10 transition-all flex items-center justify-center gap-1.5"
        >
          <RotateCcw className="w-3 h-3" /> RESET ALL
        </button>
      </div>
    </aside>
  );
}
