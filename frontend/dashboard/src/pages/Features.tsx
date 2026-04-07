import ShieldSidebar from "@/components/dashboard/ShieldSidebar";

const features = [
  { name: "Typing Dynamics", description: "Inter-key delay, hold time, flight time analysis", status: "Active", weight: "25%" },
  { name: "Navigation Patterns", description: "Page flow, click sequences, time-on-page", status: "Active", weight: "20%" },
  { name: "Device Fingerprint", description: "Browser, OS, screen, WebGL hash", status: "Active", weight: "20%" },
  { name: "SIM/Telecom Signals", description: "SIM swap detection, number porting events", status: "Active", weight: "15%" },
  { name: "Geolocation", description: "IP geolocation, impossible travel detection", status: "Active", weight: "10%" },
  { name: "Mouse Dynamics", description: "Velocity, acceleration, curvature analysis", status: "Beta", weight: "10%" },
];

const Features = () => (
  <div className="flex min-h-screen w-full bg-background">
    <ShieldSidebar />
    <main className="flex-1 p-6">
      <h1 className="text-xl font-bold mb-1">Features</h1>
      <p className="text-sm text-shield-muted mb-6">Behavioral biometric feature configuration</p>
      <div className="grid gap-4 max-w-3xl">
        {features.map((f) => (
          <div key={f.name} className="bg-card rounded-xl border border-border shadow-sm p-4 flex items-center justify-between">
            <div>
              <div className="font-semibold text-sm">{f.name}</div>
              <div className="text-xs text-shield-muted mt-0.5">{f.description}</div>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm text-shield-muted">{f.weight}</span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                f.status === "Active" ? "bg-shield-safe/10 text-shield-safe" : "bg-shield-warning/10 text-shield-warning"
              }`}>{f.status}</span>
            </div>
          </div>
        ))}
      </div>
    </main>
  </div>
);

export default Features;
