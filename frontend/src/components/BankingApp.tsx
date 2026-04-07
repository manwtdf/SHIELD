import React, { useState } from 'react';
import { Shield, Lock, CreditCard, Send, CheckCircle, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface BankingAppProps {
  onTransactionStart: () => void;
  isAccountFrozen: boolean;
  onLogout: () => void;
}

export const BankingApp: React.FC<BankingAppProps> = ({ 
  onTransactionStart, 
  isAccountFrozen, 
  onLogout 
}) => {
  const [activeScreen, setActiveScreen] = useState<'LOGIN' | 'DASHBOARD' | 'TRANSFER' | 'OTP'>('LOGIN');
  const [amount, setAmount] = useState('15000');
  const [beneficiary, setBeneficiary] = useState('Rajesh Sharma');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveScreen('DASHBOARD');
  };

  const handleTransfer = (e: React.FormEvent) => {
    e.preventDefault();
    onTransactionStart();
    setActiveScreen('OTP');
  };

  if (isAccountFrozen) {
    return (
      <div className="bg-slate-900 text-white rounded-2xl shadow-2xl p-8 w-full max-w-md border border-red-500/50 flex flex-col items-center justify-center space-y-4">
        <AlertTriangle className="text-red-500 w-16 h-16" />
        <h2 className="text-2xl font-bold">Transaction Blocked</h2>
        <p className="text-slate-400 text-center">
          Unusual behavioral patterns detected. For your security, this transaction and your account have been temporarily restricted.
        </p>
        <div className="bg-red-950/30 text-red-500 px-4 py-2 rounded-lg text-sm border border-red-500/30">
          🔒 ACCOUNT FROZEN
        </div>
        <button 
          onClick={onLogout}
          className="mt-4 px-6 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm transition-colors"
        >
          Return to Login
        </button>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 text-white rounded-2xl shadow-2xl w-full max-w-md h-[600px] flex flex-col overflow-hidden relative border border-slate-800">
      {/* Header */}
      <div className="p-6 flex items-center justify-between border-b border-slate-800 bg-slate-950/50">
        <div className="flex items-center space-x-2">
          <div className="bg-amber-500/20 p-2 rounded-lg">
            <CreditCard className="text-amber-500 w-5 h-5" />
          </div>
          <span className="font-bold tracking-tight">INDRA BANK</span>
        </div>
        <div className="flex items-center space-x-1">
          <Shield className="w-4 h-4 text-emerald-500" />
          <span className="text-[10px] text-emerald-500 font-bold uppercase tracking-widest">BehaviorShield Active</span>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {activeScreen === 'LOGIN' && (
          <motion.form 
            key="login"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            onSubmit={handleLogin}
            className="p-8 space-y-6"
          >
            <div className="space-y-4">
              <h1 className="text-3xl font-bold">Welcome Back</h1>
              <p className="text-slate-400">Secure entry to your personal banking.</p>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Customer ID</label>
              <input 
                type="text" 
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all" 
                placeholder="XXXX-XXXX"
                defaultValue="ATHARVA01"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Password</label>
              <input 
                type="password" 
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all" 
                placeholder="••••••••"
                defaultValue="password123"
              />
            </div>

            <button 
              type="submit"
              className="w-full bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold py-4 rounded-xl shadow-lg shadow-amber-500/20 transition-all flex items-center justify-center"
            >
              Sign In <Lock className="ml-2 w-4 h-4" />
            </button>
          </motion.form>
        )}

        {activeScreen === 'DASHBOARD' && (
          <motion.div 
            key="dashboard"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-6 space-y-6 flex-1 overflow-y-auto"
          >
            <div className="bg-gradient-to-br from-amber-500/10 to-slate-900 border border-amber-500/20 p-6 rounded-2xl">
              <div className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Available Balance</div>
              <div className="text-4xl font-bold">₹3,42,580<span className="text-slate-500 font-normal">.00</span></div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-bold">Recent Activity</span>
                <span className="text-amber-500 text-sm">View All</span>
              </div>
              <div className="space-y-3">
                {[
                  { desc: 'Swiggy Food', amt: '-₹450', color: 'text-red-400' },
                  { desc: 'Salary Credit', amt: '+₹85,000', color: 'text-emerald-400' },
                  { desc: 'Netflix Subscription', amt: '-₹799', color: 'text-red-400' }
                ].map((t, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl border border-slate-800">
                    <span className="text-sm">{t.desc}</span>
                    <span className={`text-sm font-bold ${t.color}`}>{t.amt}</span>
                  </div>
                ))}
              </div>
            </div>

            <button 
              onClick={() => setActiveScreen('TRANSFER')}
              className="w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 font-bold py-4 rounded-xl flex items-center justify-center transition-colors"
            >
              <Send className="mr-2 w-4 h-4 text-amber-500" /> Send Money
            </button>
          </motion.div>
        )}

        {activeScreen === 'TRANSFER' && (
          <motion.form 
            key="transfer"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            onSubmit={handleTransfer}
            className="p-8 space-y-6"
          >
            <div className="space-y-4">
              <h2 className="text-2xl font-bold">Transfer Funds</h2>
              <p className="text-slate-400 text-sm">Send money via IMPS/NEFT instantly.</p>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Beneficiary Name</label>
              <input 
                type="text" 
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 focus:outline-none" 
                value={beneficiary}
                onChange={(e) => setBeneficiary(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Amount (INR)</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 font-bold">₹</span>
                <input 
                  type="number" 
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 focus:outline-none text-2xl font-bold" 
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
            </div>

            <button 
              type="submit"
              className="w-full bg-amber-500 text-slate-950 font-bold py-4 rounded-xl"
            >
              Continue to OTP
            </button>
          </motion.form>
        )}

        {activeScreen === 'OTP' && (
          <motion.div 
            key="otp"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-8 space-y-8 flex flex-col items-center justify-center flex-1"
          >
            <div className="text-center space-y-4">
              <div className="bg-amber-500/10 p-4 rounded-full inline-block">
                <Shield className="text-amber-500 w-12 h-12" />
              </div>
              <h2 className="text-2xl font-bold">OTP Verification</h2>
              <p className="text-slate-400 text-sm">Enter the 6-digit code sent to your registered mobile ending in •••• 9102</p>
            </div>

            <div className="flex space-x-2">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="w-12 h-14 bg-slate-800 border border-slate-700 rounded-xl flex items-center justify-center text-xl font-bold animate-pulse">
                   _
                </div>
              ))}
            </div>

            <div className="text-amber-500 text-xs font-bold uppercase tracking-widest animate-pulse">
              Security scan in progress...
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
