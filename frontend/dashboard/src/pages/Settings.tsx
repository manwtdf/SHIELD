import ShieldSidebar from "@/components/dashboard/ShieldSidebar";

const Settings = () => (
  <div className="flex min-h-screen w-full bg-background">
    <ShieldSidebar />
    <main className="flex-1 p-6">
      <h1 className="text-xl font-bold mb-1">Settings</h1>
      <p className="text-sm text-shield-muted mb-6">System configuration</p>
      <div className="max-w-lg space-y-6">
        {[
          { label: "Score threshold — Step-Up Auth", value: "45" },
          { label: "Score threshold — Block", value: "30" },
          { label: "Polling interval (ms)", value: "2000" },
          { label: "SIM swap API endpoint", value: "https://telecom.api/sim-status" },
        ].map((s) => (
          <div key={s.label} className="space-y-1.5">
            <label className="text-sm font-medium">{s.label}</label>
            <input
              type="text"
              defaultValue={s.value}
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        ))}
      </div>
    </main>
  </div>
);

export default Settings;
