import { motion } from "framer-motion";

const anomalies = [
  { id: 1, text: "Typing inter-key delay +80% above baseline", z: "z = 3.8" },
  { id: 2, text: "Navigation: went directly to transfer — atypical", z: "p = 0.04" },
  { id: 3, text: "Device fingerprint: never seen for this account", z: "new" },
  { id: 4, text: "SIM swap event detected 6 minutes ago (telecom API)", z: "event" },
];

const AnomalyList = () => {
  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-5 flex-1">
      <h3 className="font-semibold text-sm mb-4">Top Anomalies — Why we blocked this</h3>
      <div className="space-y-2">
        {anomalies.map((a, i) => (
          <motion.div
            key={a.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 1.5, duration: 0.5 }}
            className="flex items-center gap-3 p-3 rounded-lg bg-accent/50 border border-border"
          >
            <span className="w-6 h-6 rounded-full bg-shield-critical/10 text-shield-critical text-xs font-bold flex items-center justify-center shrink-0">
              {a.id}
            </span>
            <span className="text-sm flex-1">{a.text}</span>
            <span className="font-mono text-xs text-shield-muted bg-accent px-2 py-0.5 rounded">
              {a.z}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default AnomalyList;
