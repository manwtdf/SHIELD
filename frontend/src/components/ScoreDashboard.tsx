import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Shield, AlertCircle, CheckCircle, Activity, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ScoreDashboardProps {
  score: number;
  history: { time: string, score: number }[];
  riskLevel: string;
  anomalies: string[];
  simSwapActive: boolean;
}

const RISK_LEVELS: Record<string, { color: string, label: string, action: string }> = {
  "LOW": { color: "text-emerald-500", label: "LOW RISK", action: "No intervention needed" },
  "MEDIUM": { color: "text-amber-500", label: "MEDIUM RISK", action: "Step-up auth recommended" },
  "HIGH": { color: "text-orange-500", label: "HIGH RISK", action: "Transaction pending review" },
  "CRITICAL": { color: "text-red-500", label: "CRITICAL ALERT", action: "BLOCK + FREEZE ACTIVE" }
};

export const ScoreDashboard: React.FC<ScoreDashboardProps> = ({
  score,
  history,
  riskLevel,
  anomalies,
  simSwapActive
}) => {
  const currentRisk = RISK_LEVELS[riskLevel] || RISK_LEVELS["LOW"];

  return (
    <div className="bg-slate-900 text-white rounded-2xl shadow-2xl p-8 w-full border border-slate-800 flex flex-col space-y-8 backdrop-blur-xl bg-slate-900/80">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-emerald-500/20 p-2 rounded-xl">
            <Shield className="text-emerald-500 w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold uppercase tracking-tight">Behavioral Intelligence</h2>
            <p className="text-slate-400 text-xs">Live session monitoring active</p>
          </div>
        </div>
        
        {sim_swap_active && (
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="flex items-center space-x-2 bg-red-500/10 border border-red-500/30 px-3 py-1.5 rounded-full animate-pulse"
          >
            <div className="w-2 h-2 bg-red-500 rounded-full" />
            <span className="text-red-500 text-[10px] font-bold uppercase tracking-widest">SIM Swap Active</span>
          </motion.div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        {/* Score Display */}
        <div className="flex flex-col items-center justify-center p-8 bg-slate-950/50 rounded-3xl border border-slate-800/50">
          <motion.div 
            key={score}
            initial={{ scale: 1.2, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className={`text-8xl font-black ${currentRisk.color} tabular-nums`}
          >
            {score}
          </motion.div>
          <div className="text-slate-500 font-bold uppercase tracking-widest text-[10px] mt-2">Confidence Score</div>
          
          <div className={`mt-6 px-4 py-1.5 rounded-full border ${currentRisk.color.replace('text', 'border')}/30 bg-white/5 flex items-center space-x-2`}>
            <Activity className={`w-4 h-4 ${currentRisk.color}`} />
            <span className={`text-xs font-black uppercase tracking-widest ${currentRisk.color}`}>{currentRisk.label}</span>
          </div>
        </div>

        {/* History Chart */}
        <div className="h-48 w-full border-l border-slate-800 pl-4">
          <div className="text-slate-500 text-[10px] font-bold uppercase tracking-widest mb-4 flex items-center">
             Session Trend <Info className="w-3 h-3 ml-1 opacity-50" />
          </div>
          <ResponsiveContainer width="100%" height="80%">
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="time" hide />
              <YAxis domain={[0, 100]} hide />
              <Tooltip 
                contentStyle={{ backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '10px' }}
                itemStyle={{ color: '#fff' }}
              />
              <Line 
                type="monotone" 
                dataKey="score" 
                stroke={score < 45 ? "#ef4444" : "#10b981"} 
                strokeWidth={3} 
                dot={{ r: 4, fill: '#0f172a', strokeWidth: 2 }}
                activeDot={{ r: 6, strokeWidth: 0 }}
                animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center">
          <AlertCircle className="w-4 h-4 mr-2" /> Top Anomalies Detected
        </h3>
        <div className="space-y-2">
          <AnimatePresence>
            {anomalies.length > 0 ? (
              anomalies.map((a, i) => (
                <motion.div 
                  key={a}
                  initial={{ x: -10, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-center space-x-3 p-3 bg-red-500/5 rounded-xl border border-red-500/10"
                >
                  <div className="text-red-500">•</div>
                  <span className="text-xs text-slate-300">{a}</span>
                </motion.div>
              ))
            ) : (
              <div className="flex items-center space-x-2 p-3 bg-emerald-500/5 rounded-xl border border-emerald-500/10">
                <CheckCircle className="text-emerald-500 w-4 h-4" />
                <span className="text-xs text-slate-400">Behavior matches baseline fingerprint.</span>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
