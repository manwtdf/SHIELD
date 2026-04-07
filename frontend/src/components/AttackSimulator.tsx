import React from 'react';
import { Play, Zap, RefreshCcw, UserCheck, ShieldAlert } from 'lucide-react';

interface AttackSimulatorProps {
  onEnroll: () => void;
  onStartLegit: () => void;
  onTriggerSimSwap: () => void;
  onStartAttack: () => void;
  onReset: () => void;
  status: string;
}

export const AttackSimulator: React.FC<AttackSimulatorProps> = ({
  onEnroll,
  onStartLegit,
  onTriggerSimSwap,
  onStartAttack,
  onReset,
  status
}) => {
  return (
    <div className="bg-slate-950 border border-slate-800 p-6 rounded-2xl flex flex-col space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <h3 className="font-bold text-slate-100 flex items-center">
           Demo Controls <Zap className="w-4 h-4 ml-2 text-amber-500 fill-amber-500" />
        </h3>
        <div className="text-[10px] bg-emerald-500/10 text-emerald-500 px-2 py-0.5 rounded uppercase font-bold tracking-widest">
           System Ready
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        <button 
          onClick={onEnroll}
          className="flex items-center space-x-3 p-3 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 hover:border-emerald-500/30 rounded-xl transition-all group"
        >
          <div className="bg-slate-900 p-2 rounded-lg group-hover:bg-emerald-500/20 transition-colors">
            <UserCheck className="w-4 h-4 text-slate-400 group-hover:text-emerald-500" />
          </div>
          <div className="text-left">
            <div className="text-xs font-bold">1. Enroll UserBaseline</div>
            <div className="text-[10px] text-slate-500">Train One-Class SVM on 10 sessions</div>
          </div>
        </button>

        <button 
          onClick={onStartLegit}
          className="flex items-center space-x-3 p-3 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 hover:border-blue-500/30 rounded-xl transition-all group"
        >
          <div className="bg-slate-900 p-2 rounded-lg group-hover:bg-blue-500/20 transition-colors">
            <Play className="w-4 h-4 text-slate-400 group-hover:text-blue-500" />
          </div>
          <div className="text-left">
            <div className="text-xs font-bold">2. Start Legit Session</div>
            <div className="text-[10px] text-slate-500">Simulate typical user behavior</div>
          </div>
        </button>

        <button 
          onClick={onTriggerSimSwap}
          className="flex items-center space-x-3 p-3 bg-red-500/5 hover:bg-red-500/10 border border-red-500/20 hover:border-red-500/50 rounded-xl transition-all group"
        >
          <div className="bg-slate-900 p-2 rounded-lg group-hover:bg-red-500/20 transition-colors">
            <Zap className="w-4 h-4 text-red-500/50 group-hover:text-red-500" />
          </div>
          <div className="text-left">
            <div className="text-xs font-bold text-red-500">3. TRIGGER SIM SWAP</div>
            <div className="text-[10px] text-red-500/50">Fire external telecom alert</div>
          </div>
        </button>

        <button 
          onClick={onStartAttack}
          className="flex items-center space-x-3 p-3 bg-orange-500/5 hover:bg-orange-500/10 border border-orange-500/20 hover:border-orange-500/50 rounded-xl transition-all group"
        >
          <div className="bg-slate-900 p-2 rounded-lg group-hover:bg-orange-500/20 transition-colors">
            <ShieldAlert className="w-4 h-4 text-orange-500/50 group-hover:text-orange-500" />
          </div>
          <div className="text-left">
            <div className="text-xs font-bold text-orange-500">4. Run Attack Protocol</div>
            <div className="text-[10px] text-orange-500/50">Simulate behavioral drift across snapshots</div>
          </div>
        </button>

        <button 
          onClick={onReset}
          className="flex items-center space-x-3 p-3 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all group mt-2"
        >
          <div className="bg-slate-900 p-2 rounded-lg group-hover:bg-slate-700 transition-colors">
            <RefreshCcw className="w-4 h-4 text-slate-500 group-hover:text-slate-300" />
          </div>
          <div className="text-left font-bold text-xs text-slate-400 group-hover:text-slate-200">Reset Demo State</div>
        </button>
      </div>

      <div className="pt-4 border-t border-slate-800 mt-2">
        <div className="bg-slate-900 px-4 py-3 rounded-xl border border-slate-800">
           <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1 italic">Event Log</div>
           <div className="text-[11px] text-emerald-400 font-mono">{status}</div>
        </div>
      </div>
    </div>
  );
};
