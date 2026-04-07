import { useMemo } from 'react';
import { Lock, Shield, UserCheck } from 'lucide-react';

interface OrbVisualizationProps {
  score: number | null;
  phase: 'idle' | 'enrolling' | 'attacking' | 'blocked' | 'allowed';
  anomalyCount: number;
}

const ORBS = [
  { label: 'Device', radius: 130, size: 36 },
  { label: 'SIM', radius: 140, size: 30 },
  { label: 'Typing', radius: 125, size: 32 },
  { label: 'Location', radius: 145, size: 34 },
  { label: 'Network', radius: 130, size: 28 },
  { label: 'Browser', radius: 135, size: 30 },
  { label: 'Behavior', radius: 140, size: 32 },
  { label: 'Velocity', radius: 125, size: 28 },
];

export default function OrbVisualization({ score, phase, anomalyCount }: OrbVisualizationProps) {
  const centerColor = useMemo(() => {
    if (phase === 'blocked') return 'from-red-600 to-red-900';
    if (phase === 'allowed') return 'from-emerald-500 to-emerald-800';
    if (phase === 'attacking') return 'from-amber-500 to-amber-800';
    return 'from-cyan-500/50 to-blue-900/50';
  }, [phase]);

  const centerGlow = useMemo(() => {
    if (phase === 'blocked') return '0 0 60px rgba(255,59,59,0.5), 0 0 120px rgba(255,59,59,0.2)';
    if (phase === 'allowed') return '0 0 60px rgba(0,255,136,0.4), 0 0 120px rgba(0,255,136,0.15)';
    if (phase === 'attacking') return '0 0 40px rgba(245,158,11,0.4)';
    return '0 0 30px rgba(59,130,246,0.2)';
  }, [phase]);

  const frozen = phase === 'blocked';

  // Generate dynamic keyframes style tag
  const orbitStyles = useMemo(() => {
    return ORBS.map((orb, i) => {
      const duration = 8 + i * 2;
      const baseAngle = (i * 360) / ORBS.length;
      return `
        @keyframes orb-spin-${i} {
          from { transform: rotate(${baseAngle}deg) translateX(${orb.radius}px) rotate(-${baseAngle}deg); }
          to { transform: rotate(${baseAngle + 360}deg) translateX(${orb.radius}px) rotate(-${baseAngle + 360}deg); }
        }
        @keyframes orb-counter-${i} {
          from { transform: rotate(${baseAngle}deg); }
          to { transform: rotate(${baseAngle + 360}deg); }
        }
      `;
    }).join('\n');
  }, []);

  return (
    <div className="relative w-[350px] h-[350px] mx-auto my-8">
      <style>{orbitStyles}</style>

      {/* Orbit rings */}
      {[120, 140, 160].map((r) => (
        <div
          key={r}
          className="absolute rounded-full border border-shield-border/20"
          style={{
            width: r * 2,
            height: r * 2,
            left: `calc(50% - ${r}px)`,
            top: `calc(50% - ${r}px)`,
          }}
        />
      ))}

      {/* Scan ring effect */}
      {phase === 'attacking' && (
        <div
          className="absolute rounded-full border-2 border-shield-amber/30"
          style={{
            width: 300,
            height: 300,
            left: 'calc(50% - 150px)',
            top: 'calc(50% - 150px)',
            animation: 'pulse 2s ease-in-out infinite',
          }}
        />
      )}

      {/* Orbiting signals */}
      {ORBS.map((orb, i) => {
        const isRed = i < anomalyCount;
        const duration = frozen ? 0 : 8 + i * 2;

        return (
          <div
            key={orb.label}
            className="absolute"
            style={{
              left: '50%',
              top: '50%',
              width: 0,
              height: 0,
              animation: frozen ? 'none' : `orb-spin-${i} ${duration}s linear infinite`,
            }}
          >
            <div
              className={`absolute flex items-center justify-center rounded-full border text-[9px] font-mono transition-all duration-500`}
              style={{
                width: orb.size,
                height: orb.size,
                marginLeft: -orb.size / 2,
                marginTop: -orb.size / 2,
                backgroundColor: isRed ? 'rgba(255,59,59,0.15)' : 'rgba(0,255,136,0.08)',
                borderColor: isRed ? 'rgba(255,59,59,0.6)' : 'rgba(0,255,136,0.3)',
                color: isRed ? '#FF3B3B' : 'rgba(0,255,136,0.7)',
                boxShadow: isRed ? '0 0 14px rgba(255,59,59,0.4)' : 'none',
              }}
            >
              {orb.label.slice(0, 3)}
            </div>
          </div>
        );
      })}

      {/* Center circle */}
      <div
        className={`absolute rounded-full bg-gradient-to-br ${centerColor} flex flex-col items-center justify-center transition-all duration-700`}
        style={{
          width: 120,
          height: 120,
          left: 'calc(50% - 60px)',
          top: 'calc(50% - 60px)',
          boxShadow: centerGlow,
        }}
      >
        {phase === 'blocked' && <Lock className="w-6 h-6 text-foreground mb-1" />}
        {phase === 'allowed' && <UserCheck className="w-6 h-6 text-foreground mb-1" />}
        {phase === 'idle' && <Shield className="w-6 h-6 text-foreground/50 mb-1" />}
        {score !== null ? (
          <>
            <span className="font-mono text-2xl font-bold text-foreground">{score}</span>
            <span className="text-[10px] text-foreground/60 font-mono">SCORE</span>
          </>
        ) : (
          <span className="text-xs text-foreground/40 font-mono">READY</span>
        )}
      </div>
    </div>
  );
}
