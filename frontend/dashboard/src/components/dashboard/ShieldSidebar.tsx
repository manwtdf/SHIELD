import { Shield, LayoutDashboard, Monitor, Bell, Layers, BookOpen, Settings } from "lucide-react";
import { NavLink } from "@/components/NavLink";

const navItems = [
  { title: "Overview", icon: LayoutDashboard, url: "/dashboard" },
  { title: "Sessions", icon: Monitor, url: "/dashboard/sessions" },
  { title: "Alerts", icon: Bell, url: "/dashboard/alerts" },
  { title: "Features", icon: Layers, url: "/dashboard/features" },
  { title: "Scenarios", icon: BookOpen, url: "/dashboard/scenarios" },
  { title: "Settings", icon: Settings, url: "/dashboard/settings" },
];

const ShieldSidebar = () => {
  return (
    <aside className="w-60 shrink-0 border-r border-border bg-card flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="p-6 flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-foreground flex items-center justify-center">
          <Shield className="w-5 h-5 text-primary-foreground" />
        </div>
        <div>
          <div className="font-bold text-sm tracking-tight">SHIELD</div>
          <div className="text-xs text-shield-muted">Fraud Detection</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-1 mt-2">
        {navItems.map((item) => (
          <NavLink
            key={item.title}
            to={item.url}
            end={item.url === "/dashboard"}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-shield-muted hover:bg-accent transition-colors"
            activeClassName="bg-accent text-foreground font-semibold"
          >
            <item.icon className="w-4 h-4" />
            <span>{item.title}</span>
          </NavLink>
        ))}
      </nav>

      {/* Analyst */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-shield-safe/20 text-shield-safe flex items-center justify-center text-xs font-bold">
            AG
          </div>
          <div>
            <div className="text-sm font-medium">Austin Green</div>
            <div className="text-xs text-shield-muted">Fraud Ops</div>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default ShieldSidebar;
