import React, { useState, useEffect } from 'react';
import { Shield, Lock, CreditCard, CheckCircle, AlertTriangle, Home, Clock, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { useBehaviorSDK } from '../hooks/useBehaviorSDK';
import { SandboxController } from '../components/sandbox/SandboxController';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

/* ─── Phone Frame Wrapper ─── */
const PhoneFrame = ({ children }: { children: React.ReactNode }) => (
  <div className="relative mx-auto" style={{ width: 375 }}>
    {/* Phone body */}
    <div className="relative bg-gray-800 border-[12px] border-gray-800 rounded-[3rem] shadow-2xl overflow-hidden" style={{ height: 812 }}>
      {/* Notch */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[120px] h-[22px] bg-gray-800 rounded-b-[1rem] z-50" />
      {/* Side buttons */}
      <div className="absolute -left-[15px] top-[120px] w-[3px] h-[40px] bg-gray-800 rounded-l-lg" />
      <div className="absolute -left-[15px] top-[170px] w-[3px] h-[40px] bg-gray-800 rounded-l-lg" />
      <div className="absolute -right-[15px] top-[140px] w-[3px] h-[55px] bg-gray-800 rounded-r-lg" />
      {/* Screen */}
      <div className="relative rounded-[2.2rem] overflow-hidden w-full h-full bg-slate-950">
        {children}
      </div>
    </div>
  </div>
);

/* ─── Main Banking App Component ─── */
export const BankingAppPage = () => {
  const [activeScreen, setActiveScreen] = useState<'LOGIN' | 'DASHBOARD' | 'TRANSFER' | 'OTP' | 'SUCCESS' | 'FROZEN'>('LOGIN');
  const [amount, setAmount] = useState('15000');
  const [isFrozen, setIsFrozen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  // Sandbox State
  const [sandboxMode, setSandboxMode] = useState<'OFF' | 'TRAINING' | 'TESTING'>('OFF');
  const targetUserId = sandboxMode === 'OFF' ? 1 : 1;
  const sessionType = sandboxMode === 'TESTING' ? 'attacker' : 'legitimate';

  // Initialize behavioral tracking SDK
  const { currentScore, riskLevel, anomalies, captureAndFeedData } = useBehaviorSDK(targetUserId, sessionId);

  // Poll for freeze status
  useEffect(() => {
    if (!sessionId) return;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${BACKEND_URL}/score/${sessionId}`);
        if (res.data.action === 'BLOCK_AND_FREEZE') {
          setIsFrozen(true);
          setActiveScreen('FROZEN');
          clearInterval(interval);
        }
      } catch {
        // Backend unavailable
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId) {
      try {
        const res = await axios.post(`${BACKEND_URL}/session/start`, {
          user_id: targetUserId,
          session_type: sessionType
        });
        setSessionId(res.data.session_id);
        localStorage.setItem('shieldSessionId', res.data.session_id);
      } catch (err) {
        console.error("Session start failed", err);
      }
    }
    setActiveScreen('DASHBOARD');
  };

  const handleTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    setActiveScreen('OTP');
    setTimeout(() => {
      if (isFrozen) {
        setActiveScreen('FROZEN');
      } else {
        setActiveScreen('SUCCESS');
      }
    }, 4000);
  };

  const handleLogout = () => {
    setSessionId(null);
    localStorage.removeItem('shieldSessionId');
    setIsFrozen(false);
    setActiveScreen('LOGIN');
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-8 pb-28">
      {/* Sandbox Controller Overlay */}
      <SandboxController 
        userId={1}
        mode={sandboxMode}
        setMode={setSandboxMode}
        currentScore={currentScore}
        riskLevel={riskLevel}
        anomalies={anomalies}
        captureAndFeedData={sandboxMode === 'OFF' ? undefined : captureAndFeedData}
      />
      
      <PhoneFrame>
        <div className="relative h-full flex flex-col overflow-hidden no-scrollbar" style={{ fontFamily: "'Inter', 'Manrope', sans-serif" }}>

          {/* ─── Top Status Bar ─── */}
          <nav className="sticky top-0 w-full z-50 glass px-5 py-3.5 flex justify-between items-center">
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 bg-brand-gold rounded-lg flex items-center justify-center font-extrabold text-slate-950 text-xs">IB</div>
              <span className="font-bold text-base tracking-tight">INDRA BANK</span>
            </div>
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full border border-brand-gold/20 bg-brand-gold/5 shield-active">
              <div className="w-1.5 h-1.5 rounded-full bg-brand-gold animate-ping" />
              <span className="text-[8px] font-bold text-brand-gold uppercase tracking-widest">BehaviorShield</span>
            </div>
          </nav>

          {/* ─── Screen Content ─── */}
          <div className="flex-1 overflow-y-auto no-scrollbar">
            <AnimatePresence mode="wait">

              {/* LOGIN */}
              {activeScreen === 'LOGIN' && (
                <motion.form
                  key="login"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  onSubmit={handleLogin}
                  className="p-7 space-y-6 pt-10"
                >
                  <div className="space-y-3">
                    <h1 className="text-3xl font-extrabold tracking-tight">Welcome Back</h1>
                    <p className="text-slate-400 text-sm">Secure entry to your personal banking.</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Customer ID</label>
                    <input
                      type="text"
                      className="w-full bg-slate-900 border border-slate-800 rounded-2xl px-5 py-4 text-sm focus:outline-none focus:border-brand-gold/50 transition-colors"
                      defaultValue="ATHARVA01"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Password</label>
                    <input
                      type="password"
                      className="w-full bg-slate-900 border border-slate-800 rounded-2xl px-5 py-4 text-sm focus:outline-none focus:border-brand-gold/50 transition-colors"
                      defaultValue="password123"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-brand-gold py-4 rounded-2xl text-slate-950 font-black text-sm shadow-lg shadow-brand-gold/20 hover:scale-[1.02] active:scale-95 transition-all uppercase tracking-widest flex items-center justify-center"
                  >
                    Sign In <Lock className="ml-2 w-4 h-4" />
                  </button>
                </motion.form>
              )}

              {/* DASHBOARD */}
              {activeScreen === 'DASHBOARD' && (
                <motion.div
                  key="dashboard"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="p-6 space-y-7 pb-24"
                >
                  <header>
                    <h1 className="text-2xl font-extrabold tracking-tight">Welcome, John Kumar</h1>
                    <p className="text-slate-400 text-sm mt-1">Ac: 49XX XXXX XXXX 4521</p>
                  </header>

                  {/* Balance Card with Glow */}
                  <div className="relative group cursor-pointer">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-brand-gold to-amber-600 rounded-3xl blur opacity-20 group-hover:opacity-40 transition duration-1000" />
                    <div className="relative bg-slate-900 border border-slate-800 p-7 rounded-3xl space-y-5">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="text-[10px] font-bold text-brand-gold uppercase tracking-[0.2em] mb-1">Available Balance</p>
                          <h2 className="text-3xl font-extrabold tracking-tight">INR3,42,580.00</h2>
                        </div>
                        <div className="p-3 bg-slate-800 rounded-2xl">
                          <CreditCard className="w-5 h-5 text-brand-gold" />
                        </div>
                      </div>
                      <div className="flex space-x-3">
                        <button
                          onClick={() => setActiveScreen('TRANSFER')}
                          className="flex-1 bg-brand-gold py-3 rounded-xl text-slate-950 font-bold text-sm hover:scale-[1.02] active:scale-95 transition-all"
                        >
                          Transfer
                        </button>
                        <button className="flex-1 bg-slate-800 py-3 rounded-xl text-slate-100 font-bold text-sm hover:bg-slate-700 transition-all">
                          Details
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Behavioral Snapshot */}
                  <section className="space-y-3">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest px-1 text-center">Behavioral Snapshot</h3>
                    <div className="grid grid-cols-4 gap-3">
                      {[
                        { emoji: '📱', label: 'Device' },
                        { emoji: '⌨️', label: 'Typing' },
                        { emoji: '📍', label: 'Loc' },
                        { emoji: '⚡', label: 'Action' },
                      ].map((item) => (
                        <div key={item.label} className="flex flex-col items-center space-y-1.5">
                          <div className="w-12 h-12 bg-slate-900 border border-slate-800 rounded-2xl flex items-center justify-center text-lg">
                            {item.emoji}
                          </div>
                          <span className="text-[10px] font-bold text-slate-500">{item.label}</span>
                        </div>
                      ))}
                    </div>
                  </section>

                  {/* Recent Activity */}
                  <section className="space-y-3">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest px-1">Recent Activity</h3>
                    {[
                      { name: 'Grocery Store', amount: '-INR2,450.00', time: 'Today' },
                      { name: 'Salary Credit', amount: '+INR85,000.00', time: 'Yesterday' },
                      { name: 'Electric Bill', amount: '-INR1,890.00', time: '2 days ago' },
                    ].map((tx) => (
                      <div key={tx.name} className="flex items-center justify-between p-4 bg-slate-900 border border-slate-800 rounded-2xl">
                        <div>
                          <div className="text-sm font-bold">{tx.name}</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">{tx.time}</div>
                        </div>
                        <div className={`text-sm font-bold ${tx.amount.startsWith('+') ? 'text-shield-safe' : 'text-slate-300'}`}>
                          {tx.amount}
                        </div>
                      </div>
                    ))}
                  </section>
                </motion.div>
              )}

              {/* TRANSFER */}
              {activeScreen === 'TRANSFER' && (
                <motion.form
                  key="transfer"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  onSubmit={handleTransfer}
                  className="p-7 space-y-6 pb-24"
                >
                  <header className="flex items-center space-x-3">
                    <button onClick={() => setActiveScreen('DASHBOARD')} type="button" className="p-2 bg-slate-900 rounded-lg text-slate-400">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M15 19l-7-7 7-7" /></svg>
                    </button>
                    <h1 className="text-xl font-extrabold uppercase tracking-tight">Secure Transfer</h1>
                  </header>

                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Recipient Account</label>
                    <input
                      type="text"
                      className="w-full bg-slate-900 border border-slate-800 p-4 rounded-2xl text-sm focus:outline-none focus:border-brand-gold/50 transition-colors"
                      defaultValue="JULIAN SMITH"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">Amount</label>
                    <div className="relative">
                      <span className="absolute left-5 top-1/2 -translate-y-1/2 text-xl font-extrabold text-brand-gold">INR</span>
                      <input
                        type="number"
                        className="w-full bg-slate-900 border border-slate-800 p-6 pl-16 rounded-2xl text-3xl font-extrabold focus:outline-none focus:border-brand-gold/50 transition-colors"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                      />
                    </div>
                    <p className="text-[10px] text-slate-500 text-right italic mt-2">-- Daily Limit Remaining: INR1,42,850.00</p>
                  </div>

                  <button
                    type="submit"
                    className="w-full bg-brand-gold py-5 rounded-2xl text-slate-950 font-black text-base shadow-xl shadow-brand-gold/10 hover:scale-[1.02] active:scale-95 transition-all uppercase tracking-widest"
                  >
                    Confirm & Send
                  </button>
                </motion.form>
              )}

              {/* OTP */}
              {activeScreen === 'OTP' && (
                <motion.div
                  key="otp"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="p-7 space-y-8 flex flex-col items-center justify-center flex-1 pt-20"
                >
                  <div className="text-center space-y-4">
                    <div className="bg-brand-gold/10 p-4 rounded-full inline-block">
                      <Shield className="text-brand-gold w-12 h-12" />
                    </div>
                    <h2 className="text-xl font-bold">OTP Verification</h2>
                    <p className="text-slate-400 text-sm">Enter the 6-digit code sent to your registered mobile ending in •• 9102</p>
                  </div>
                  <div className="flex space-x-2">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                      <div key={i} className="w-10 h-12 bg-slate-800 border border-slate-700 rounded-lg flex items-center justify-center text-xl font-bold animate-pulse">
                        _
                      </div>
                    ))}
                  </div>
                  <div className="text-brand-gold text-[10px] font-bold uppercase tracking-widest animate-pulse">
                    Security scan in progress...
                  </div>
                </motion.div>
              )}

              {/* SUCCESS */}
              {activeScreen === 'SUCCESS' && (
                <motion.div
                  key="success"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="p-7 space-y-6 flex flex-col items-center justify-center flex-1 pt-20"
                >
                  <div className="w-24 h-24 bg-brand-gold/10 border-4 border-brand-gold rounded-full flex items-center justify-center animate-bounce">
                    <CheckCircle className="text-brand-gold w-12 h-12" />
                  </div>
                  <div className="text-center">
                    <h2 className="text-xl font-extrabold">✓ Transfer Success</h2>
                    <p className="text-slate-500 mt-2">Transaction ID: SH-8E8DF0F1</p>
                  </div>
                  <button
                    onClick={() => setActiveScreen('DASHBOARD')}
                    className="mt-8 px-8 py-3 bg-slate-900 border border-slate-800 rounded-xl font-bold text-sm text-slate-400 hover:bg-slate-800 transition-all"
                  >
                    Back to Dashboard
                  </button>
                </motion.div>
              )}

              {/* FROZEN */}
              {activeScreen === 'FROZEN' && (
                <motion.div
                  key="frozen"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="absolute inset-0 z-50 flex flex-col items-center justify-center p-8"
                  style={{ background: 'linear-gradient(135deg, rgba(127, 29, 29, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)' }}
                >
                  <div className="relative mb-6">
                    <div className="absolute inset-0 bg-red-500/30 rounded-full blur-2xl animate-pulse" />
                    <div className="relative bg-red-500/20 p-6 rounded-full border-2 border-red-500/50">
                      <AlertTriangle className="text-red-500 w-16 h-16" />
                    </div>
                  </div>
                  <h2 className="text-2xl font-black text-red-500 text-center uppercase tracking-wider mb-3">
                    Transaction Frozen
                  </h2>
                  <p className="text-slate-400 text-center text-sm mb-2 max-w-xs">
                    Your transaction has been frozen by S.H.I.E.L.D. Unusual behavioral patterns detected.
                  </p>
                  <div className="bg-red-950/50 text-red-500 px-6 py-3 rounded-xl text-sm border border-red-500/30 font-black uppercase tracking-widest mb-6">
                    🔒 ACCOUNT FROZEN
                  </div>
                  <p className="text-slate-500 text-xs text-center mb-6">SMS alert sent to your registered number. Please contact your bank immediately.</p>
                  <button
                    onClick={handleLogout}
                    className="px-8 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-sm font-bold transition-colors"
                  >
                    Return to Login
                  </button>
                </motion.div>
              )}

            </AnimatePresence>
          </div>

          {/* ─── Bottom Navigation Bar ─── */}
          {activeScreen !== 'FROZEN' && (
            <nav className="absolute bottom-0 w-full z-40 glass rounded-t-[2rem] px-6 py-4 pb-6 flex justify-between items-center">
              <button onClick={() => setActiveScreen('DASHBOARD')} className="text-brand-gold flex flex-col items-center">
                <Home className="w-5 h-5" />
              </button>
              <button className="text-slate-500 flex flex-col items-center">
                <Shield className="w-5 h-5" />
              </button>
              <div
                onClick={() => setActiveScreen('TRANSFER')}
                className="w-11 h-11 bg-brand-gold rounded-full flex items-center justify-center -mt-8 gold-glow border-4 border-slate-950 font-bold text-slate-950 text-xl cursor-pointer hover:scale-110 transition-transform"
              >
                +
              </div>
              <button className="text-slate-500 flex flex-col items-center">
                <Clock className="w-5 h-5" />
              </button>
              <button className="text-slate-500 flex flex-col items-center">
                <User className="w-5 h-5" />
              </button>
            </nav>
          )}

        </div>
      </PhoneFrame>
    </div>
  );
};

export default BankingAppPage;
