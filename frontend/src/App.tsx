import { useState, useEffect } from 'react';
import axios from 'axios';
import { BankingApp } from './components/BankingApp';
import { ScoreDashboard } from './components/ScoreDashboard';
import { AttackSimulator } from './components/AttackSimulator';
import { useBehaviorSDK } from './hooks/useBehaviorSDK';

const BACKEND_URL = 'http://localhost:8000';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId] = useState(1);
  const [history, setHistory] = useState<{ time: string; score: number }[]>([]);
  const [status, setStatus] = useState('System Standby');
  const [isFrozen, setIsFrozen] = useState(false);
  const [simSwapActive, setSimSwapActive] = useState(false);
  
  // Scoring state from manual dashboard polling or SDK
  const [score, setScore] = useState(91);
  const [riskLevel, setRiskLevel] = useState('LOW');
  const [anomalies, setAnomalies] = useState<string[]>([]);

  // 1. Enrollment
  const handleEnroll = async () => {
    setStatus('Initializing Enrollment...');
    try {
      await axios.post(`${BACKEND_URL}/enroll/${userId}`);
      setStatus('✓ User Atharva Kumar Enrolled (10 sessions)');
    } catch (e) {
      setStatus('Enrollment Failed. Check Backend.');
    }
  };

  // 2. Start Legit Session
  const handleStartLegit = async () => {
    setStatus('Starting Legitimate Session...');
    try {
      const res = await axios.post(`${BACKEND_URL}/session/start`, { 
        user_id: userId, 
        session_type: 'legitimate' 
      });
      setSessionId(res.data.session_id);
      setIsFrozen(false);
      setHistory([{ time: '0s', score: 91 }]);
      setScore(91);
      setRiskLevel('LOW');
      setAnomalies([]);
      setStatus('✓ Legit Session Active. Monitoring...');
    } catch (e) {
      setStatus('Failed to Start Session.');
    }
  };

  // 3. Trigger SIM Swap
  const handleTriggerSimSwap = async () => {
    setStatus('⚡ TRIGGERING SIM SWAP ALERT...');
    try {
      await axios.post(`${BACKEND_URL}/sim-swap/trigger?user_id=${userId}`);
      setSimSwapActive(true);
      setStatus('⚡ 5G SYSTEM: SIM Swap Event Confirmed.');
    } catch (e) {
      setStatus('SIM Swap Trigger Failed.');
    }
  };

  // 4. Start Attack (Progressive Degradation)
  const handleStartAttack = async () => {
    setStatus('CRITICAL: NEW SESSION DETECTED [UNRECOGNIZED DEVICE]');
    try {
      const res = await axios.post(`${BACKEND_URL}/session/start`, { 
        user_id: userId, 
        session_type: 'attacker' 
      });
      const sId = res.data.session_id;
      setSessionId(sId);
      
      // Simulate 5 snapshots revealing anomalies progressively
      const snapshots = [
        { score: 91, label: '0s', anomalies: [] },
        { score: 74, label: '6s', anomalies: ['Typing delay +80%', 'Irregular rhythm'] },
        { score: 58, label: '12s', anomalies: ['Typing delay +80%', 'Direct-to-transfer path'] },
        { score: 44, label: '18s', anomalies: ['Typing delay +80%', 'Direct-to-transfer path', 'New device fingerprint'] },
        { score: 27, label: '24s', anomalies: ['Typing delay +80%', 'Direct-to-transfer path', 'New device fingerprint', 'SIM swap event detected'] },
      ];

      for (let i = 0; i < snapshots.length; i++) {
        await new Promise(r => setTimeout(r, 2000)); // Faster for demo than 6s
        const snap = snapshots[i];
        
        // Update local state for immediate feedback
        setScore(snap.score);
        setAnomalies(snap.anomalies);
        setHistory(prev => [...prev, { time: snap.label, score: snap.score }]);
        
        if (snap.score < 45) setRiskLevel('HIGH');
        if (snap.score < 30) {
          setRiskLevel('CRITICAL');
          setIsFrozen(true);
          setStatus('🔒 ATTACK REMEDIATED: TRANSACTION BLOCKED');
        } else {
          setStatus(`Monitoring... Score: ${snap.score}`);
        }
      }
    } catch (e) {
      setStatus('Attack Simulation Failed.');
    }
  };

  const handleReset = () => {
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-slate-100 flex flex-col items-center">
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-12 gap-10">
        
        {/* Left Side: Simulation Controls */}
        <div className="lg:col-span-3 space-y-6">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
             <div className="flex items-center space-x-2 mb-6">
               <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center justify-center font-bold text-slate-950">SH</div>
               <h1 className="text-xl font-bold tracking-tight">SHIELD</h1>
             </div>
             <p className="text-xs text-slate-400 leading-relaxed">
               Session-based Heuristic Intelligence for Event Level Defense. Detecting SIM swap fraudsters via behavioral biomarkers.
             </p>
          </div>

          <AttackSimulator 
            onEnroll={handleEnroll}
            onStartLegit={handleStartLegit}
            onTriggerSimSwap={handleTriggerSimSwap}
            onStartAttack={handleStartAttack}
            onReset={handleReset}
            status={status}
          />
        </div>

        {/* Center: The Mock Bank App */}
        <div className="lg:col-span-4 flex justify-center items-start">
           <div className="sticky top-8 w-full">
             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest text-center mb-4 italic">Device Simulation (iPhone 15 Pro)</div>
             <BankingApp 
               onTransactionStart={() => setStatus('Transaction Initiated... Verification pending.')}
               isAccountFrozen={isFrozen}
               onLogout={handleReset}
             />
           </div>
        </div>

        {/* Right Side: Security Dashboard */}
        <div className="lg:col-span-5 space-y-6">
          <ScoreDashboard 
            score={score}
            history={history}
            riskLevel={riskLevel}
            anomalies={anomalies}
            simSwapActive={simSwapActive}
          />

          <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl">
             <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-4">Infrastructure health</h3>
             <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/50">
                   <div className="text-[10px] text-slate-500 uppercase font-bold">Latency</div>
                   <div className="text-lg font-bold text-emerald-500">24ms</div>
                </div>
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/50">
                   <div className="text-[10px] text-slate-500 uppercase font-bold">Accuracy</div>
                   <div className="text-lg font-bold text-emerald-500">94.8%</div>
                </div>
             </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;
