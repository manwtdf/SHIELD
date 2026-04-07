import { useState, useCallback, useRef } from 'react';
import ScenarioSidebar from '@/components/simulator/ScenarioSidebar';
import OrbVisualization from '@/components/simulator/OrbVisualization';
import DetectionTable from '@/components/simulator/DetectionTable';
import FeatureInspector from '@/components/simulator/FeatureInspector';
import LegacyContrast from '@/components/simulator/LegacyContrast';
import { SCENARIOS, type ScenarioResult, type StepStatus } from '@/components/simulator/types';

const API_BASE = 'http://localhost:8000';

const SCENARIO_SCORES: Record<number, { score: number; result: 'BLOCKED' | 'STEP-UP' | 'ALLOWED' | 'ALL FROZEN'; time: string }> = {
  1: { score: 12, result: 'BLOCKED', time: '0.8s' },
  2: { score: 18, result: 'BLOCKED', time: '1.1s' },
  3: { score: 5, result: 'ALL FROZEN', time: '0.3s' },
  4: { score: 38, result: 'STEP-UP', time: '1.4s' },
  5: { score: 15, result: 'BLOCKED', time: '0.9s' },
  6: { score: 9, result: 'BLOCKED', time: '0.6s' },
  7: { score: 91, result: 'ALLOWED', time: '0.5s' },
};

export default function Simulator() {
  const [activeScenario, setActiveScenario] = useState(1);
  const [stepStatuses, setStepStatuses] = useState<StepStatus[]>(['ready', 'pending', 'pending', 'pending']);
  const [stepData, setStepData] = useState<{ baseline?: number; elapsed?: string; snapshot?: string }>({});
  const [results, setResults] = useState<ScenarioResult[]>([]);
  const [phase, setPhase] = useState<'idle' | 'enrolling' | 'attacking' | 'blocked' | 'allowed'>('idle');
  const [score, setScore] = useState<number | null>(null);
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [showLegacy, setShowLegacy] = useState(false);
  const [showFeatures, setShowFeatures] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  const apiCall = async (url: string, method: string, body?: object) => {
    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      });
      return await res.json();
    } catch {
      // API not available, simulate locally
      return null;
    }
  };

  const updateStep = (index: number, status: StepStatus) => {
    setStepStatuses(prev => {
      const next = [...prev];
      next[index] = status;
      return next;
    });
  };

  const simulateStep = useCallback(async (step: number) => {
    const scenario = SCENARIOS.find(s => s.id === activeScenario)!;
    const scenarioData = SCENARIO_SCORES[activeScenario];

    if (step === 0) {
      // Enroll
      updateStep(0, 'active');
      setPhase('enrolling');
      apiCall(`${API_BASE}/enroll/1`, 'POST');
      await new Promise(r => setTimeout(r, 1500));
      setStepData(d => ({ ...d, baseline: 91 }));
      setScore(91);
      setPhase('idle');
      updateStep(0, 'done');
      updateStep(1, 'ready');
    } else if (step === 1) {
      // Trigger SIM swap
      updateStep(1, 'active');
      apiCall(`${API_BASE}/sim-swap/trigger`, 'POST', { user_id: 1 });
      let elapsed = 0;
      timerRef.current = setInterval(() => {
        elapsed++;
        setStepData(d => ({ ...d, elapsed: `0:${String(elapsed).padStart(2, '0')} elapsed` }));
      }, 1000);
      await new Promise(r => setTimeout(r, 3000));
      clearInterval(timerRef.current);
      updateStep(1, 'done');
      updateStep(2, 'ready');
    } else if (step === 2) {
      // Run attack
      updateStep(2, 'active');
      setPhase('attacking');
      apiCall(`${API_BASE}/scenarios/${activeScenario}/run`, 'POST', { user_id: 1 });

      // Animate anomalies appearing one by one
      const totalAnomalies = scenario.isAttack ? 8 : 1;
      for (let i = 1; i <= 5; i++) {
        setStepData(d => ({ ...d, snapshot: `Snapshot ${i}/5...` }));
        setAnomalyCount(Math.min(Math.round((i / 5) * totalAnomalies), totalAnomalies));
        setScore(Math.round(scenarioData.score + ((91 - scenarioData.score) * (5 - i)) / 5));
        await new Promise(r => setTimeout(r, 800));
      }

      setScore(scenarioData.score);
      setAnomalyCount(totalAnomalies);
      setPhase(scenario.isAttack ? 'blocked' : 'allowed');
      setShowFeatures(true);

      // Add result
      setResults(prev => [
        ...prev,
        {
          scenarioId: scenario.id,
          scenarioName: scenario.name,
          score: scenarioData.score,
          detected: scenario.isAttack,
          time: scenarioData.time,
          result: scenarioData.result,
          legacyResult: scenario.isAttack ? 'APPROVED ❌' : 'ALLOWED ✅',
        },
      ]);

      updateStep(2, 'done');
      updateStep(3, 'ready');
    } else if (step === 3) {
      // Compare legacy
      updateStep(3, 'active');
      await new Promise(r => setTimeout(r, 500));
      setShowLegacy(true);
      updateStep(3, 'done');
    }
  }, [activeScenario]);

  const handleReset = useCallback(async () => {
    clearInterval(timerRef.current);
    apiCall(`${API_BASE}/sim-swap/clear`, 'POST', { user_id: 1 });
    setStepStatuses(['ready', 'pending', 'pending', 'pending']);
    setStepData({});
    setPhase('idle');
    setScore(null);
    setAnomalyCount(0);
    setShowLegacy(false);
    setShowFeatures(false);
  }, []);

  return (
    <div
      className="h-screen flex flex-col overflow-hidden"
      style={{
        background: 'radial-gradient(ellipse at center, #0D1526 0%, #080B14 70%)',
      }}
    >
      {/* Grid overlay */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `linear-gradient(rgba(30,45,74,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(30,45,74,0.04) 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />

      {/* Top bar */}
      <header className="relative z-10 flex items-center justify-between px-6 py-3 border-b border-shield-border bg-card/80 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-shield-green/20 flex items-center justify-center">
            <span className="text-shield-green font-bold text-sm">S</span>
          </div>
          <h1 className="text-lg font-bold text-foreground tracking-tight">SHIELD</h1>
          <span className="text-xs text-muted-foreground font-mono ml-2">Attack Simulation Control Panel</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-shield-green animate-[blink_2s_ease-in-out_infinite]" />
          <span className="text-xs text-muted-foreground font-mono">LIVE</span>
        </div>
      </header>

      <div className="flex flex-1 relative z-10 overflow-hidden">
        <ScenarioSidebar
          activeScenario={activeScenario}
          onSelectScenario={(id) => { setActiveScenario(id); handleReset(); }}
          stepStatuses={stepStatuses}
          stepData={stepData}
          onRunStep={simulateStep}
          onReset={handleReset}
        />

        <main className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-2 h-2 rounded-full bg-shield-green animate-pulse" />
            <h2 className="font-mono text-xs tracking-[0.2em] text-shield-green uppercase">
              Live Scenario Output
            </h2>
            <span className="text-xs text-muted-foreground font-mono ml-2">
              — {SCENARIOS.find(s => s.id === activeScenario)?.name}
            </span>
          </div>

          <OrbVisualization score={score} phase={phase} anomalyCount={anomalyCount} />

          {showLegacy && <LegacyContrast visible={showLegacy} score={score ?? 0} />}

          <DetectionTable results={results} />
        </main>
      </div>

      <FeatureInspector visible={showFeatures} />
    </div>
  );
}
