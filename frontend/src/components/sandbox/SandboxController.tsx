import React, { useState } from 'react';
import axios from 'axios';
import { Shield, Brain, RefreshCw, Activity, Terminal } from 'lucide-react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

interface SandboxControllerProps {
  userId: number;
  mode: 'OFF' | 'TRAINING' | 'TESTING';
  setMode: (mode: 'OFF' | 'TRAINING' | 'TESTING') => void;
  currentScore: number | null;
  riskLevel: string;
  anomalies: string[];
}

export const SandboxController: React.FC<SandboxControllerProps> = ({
  userId,
  mode,
  setMode,
  currentScore,
  riskLevel,
  anomalies
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [trainingStatus, setTrainingStatus] = useState<string>('');

  const handleTrain = async () => {
    setTrainingStatus('Training...');
    try {
      const res = await axios.post(`${BACKEND_URL}/enroll/${userId}`);
      if (res.data.enrolled) {
        setTrainingStatus(`Model Trained on ${res.data.sessions_used} sessions.`);
      } else {
        setTrainingStatus(`Need more sessions. Currently have ${res.data.sessions_used}/10.`);
      }
    } catch (e: any) {
      setTrainingStatus(`Error: ${e.response?.data?.detail || e.message}`);
    }
  };

  const handleReset = async () => {
    setTrainingStatus('Resetting...');
    try {
      const res = await axios.post(`${BACKEND_URL}/enroll/reset/${userId}`);
      setTrainingStatus(`Reset ${res.data.cleared_sessions} profiles.`);
      setMode('OFF');
    } catch (e: any) {
      setTrainingStatus(`Error: ${e.response?.data?.detail || e.message}`);
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 z-50 bg-slate-900 border border-slate-700 p-3 rounded-full shadow-2xl text-brand-gold"
      >
        <Terminal className="w-6 h-6" />
      </button>
    );
  }

  return (
    <div className="fixed top-4 right-4 w-80 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-xl shadow-2xl z-50 flex flex-col font-mono text-sm overflow-hidden">
      <div className="bg-slate-800 border-b border-slate-700 p-3 flex justify-between items-center">
        <div className="flex items-center space-x-2 text-brand-gold font-bold">
          <Terminal className="w-4 h-4" />
          <span>S.H.I.E.L.D Sandbox</span>
        </div>
        <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-white transition-colors">
          ✕
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Mode Selector */}
        <div className="space-y-2">
          <label className="text-xs text-slate-400 uppercase tracking-wider font-bold">Operation Mode</label>
          <div className="flex bg-slate-950 rounded-lg p-1 border border-slate-800">
            <button 
              onClick={() => setMode('OFF')}
              className={`flex-1 py-1.5 rounded-md text-xs font-bold transition-all ${mode === 'OFF' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
            >
              OFF
            </button>
            <button 
              onClick={() => setMode('TRAINING')}
              className={`flex-1 py-1.5 rounded-md text-xs font-bold transition-all ${mode === 'TRAINING' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
            >
              TRAINING
            </button>
            <button 
              onClick={() => setMode('TESTING')}
              className={`flex-1 py-1.5 rounded-md text-xs font-bold transition-all ${mode === 'TESTING' ? 'bg-red-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
            >
              TESTING
            </button>
          </div>
        </div>

        {/* Training Controls */}
        <div className="bg-slate-950 rounded-lg p-3 border border-slate-800 space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-400">Target User ID</span>
            <span className="text-brand-gold font-bold">#{userId}</span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button 
              onClick={handleTrain}
              className="bg-blue-900/50 hover:bg-blue-800 border border-blue-700 text-blue-300 py-2 rounded-lg flex items-center justify-center space-x-1 transition-colors"
            >
              <Brain className="w-3 h-3" />
              <span className="text-[10px] uppercase font-bold">Compile ML</span>
            </button>
            <button 
              onClick={handleReset}
              className="bg-red-900/30 hover:bg-red-900/60 border border-red-900 text-red-400 py-2 rounded-lg flex items-center justify-center space-x-1 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              <span className="text-[10px] uppercase font-bold">Drop Data</span>
            </button>
          </div>
          {trainingStatus && (
            <div className="text-[10px] text-slate-400 bg-slate-900 p-2 rounded border border-slate-800">
              {trainingStatus}
            </div>
          )}
        </div>

        {/* Live HUD - Only active in testing */}
        {mode === 'TESTING' && (
          <div className="bg-slate-950 rounded-lg p-3 border border-red-900/50 space-y-3 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-600 to-brand-gold animate-pulse" />
            
            <div className="flex justify-between items-end">
              <div>
                <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Live Score</div>
                <div className={`text-3xl font-black ${
                  riskLevel === 'CRITICAL' ? 'text-red-500' :
                  riskLevel === 'HIGH' ? 'text-orange-500' :
                  riskLevel === 'MEDIUM' ? 'text-yellow-500' : 'text-green-500'
                }`}>
                  {currentScore !== null ? currentScore : '--'}
                </div>
              </div>
              <div className="text-right">
                 <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Risk Level</div>
                 <div className="text-xs font-bold text-white px-2 py-1 bg-slate-800 rounded">{riskLevel}</div>
              </div>
            </div>

            {anomalies.length > 0 && (
              <div className="pt-2 border-t border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase font-bold mb-1 flex items-center">
                  <Activity className="w-3 h-3 mr-1" /> Anomalies
                </div>
                <ul className="text-[10px] space-y-1">
                  {anomalies.map((a, i) => (
                    <li key={i} className="text-red-400 truncate border-l-2 border-red-500 pl-1">{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
