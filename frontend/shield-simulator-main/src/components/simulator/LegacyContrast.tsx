import { motion } from 'framer-motion';
import { Lock, CheckCircle } from 'lucide-react';

interface LegacyContrastProps {
  visible: boolean;
  score: number;
}

export default function LegacyContrast({ visible, score }: LegacyContrastProps) {
  if (!visible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="mt-6 grid grid-cols-2 gap-6"
    >
      {/* SHIELD Card */}
      <div className="border-2 border-shield-green rounded-lg p-6 bg-shield-green/5 shadow-[0_0_30px_hsl(153_100%_50%/0.1)]">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-shield-green/20 flex items-center justify-center">
            <Lock className="w-5 h-5 text-shield-green" />
          </div>
          <h4 className="text-lg font-bold text-shield-green font-mono">SHIELD</h4>
        </div>
        <div className="text-2xl font-bold text-shield-red font-mono mb-2">
          🔒 TRANSACTION BLOCKED
        </div>
        <div className="text-muted-foreground text-sm">
          Behavioral Score: <span className="text-foreground font-mono font-bold">{score}</span>/100
        </div>
        <div className="mt-3 text-xs text-muted-foreground font-mono space-y-1">
          <div>• Device fingerprint mismatch <span className="text-shield-red">✗</span></div>
          <div>• SIM ICCID changed <span className="text-shield-red">✗</span></div>
          <div>• Typing pattern anomaly <span className="text-shield-red">✗</span></div>
          <div>• Location deviation 12.4km <span className="text-shield-red">✗</span></div>
        </div>
      </div>

      {/* Legacy Card */}
      <div className="border-2 border-shield-red rounded-lg p-6 bg-shield-red/5 shadow-[0_0_30px_hsl(0_100%_62%/0.1)]">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-shield-red/20 flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-shield-red" />
          </div>
          <h4 className="text-lg font-bold text-shield-red font-mono">Legacy Rule-Based</h4>
        </div>
        <div className="text-2xl font-bold text-shield-green font-mono mb-2">
          ✅ TRANSACTION APPROVED
        </div>
        <div className="text-muted-foreground text-sm mb-3">
          All rule checks passed
        </div>
        <div className="text-xs font-mono space-y-1.5 text-muted-foreground">
          <div>Amount {'>'} ₹50,000? <span className="text-shield-green">No ✓</span></div>
          <div>Time {'>'} 11PM? <span className="text-shield-green">No ✓</span></div>
          <div>Location anomaly? <span className="text-shield-green">No ✓</span></div>
          <div className="pt-2 text-shield-red font-bold text-sm">
            Result: APPROVED — ₹15,000 sent to attacker
          </div>
        </div>
      </div>
    </motion.div>
  );
}
