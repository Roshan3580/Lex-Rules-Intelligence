import { Shield, Users, Tag, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";

const users = [
  { name: "Alex Cole", email: "alex@acme.com", role: "Admin", status: "active", initial: "AC" },
  { name: "Sarah Park", email: "sarah@acme.com", role: "Reviewer", status: "active", initial: "SP" },
  { name: "Marcus Chen", email: "marcus@acme.com", role: "Reviewer", status: "active", initial: "MC" },
  { name: "Diana Voss", email: "diana@acme.com", role: "Viewer", status: "invited", initial: "DV" },
];

const audit = [
  { actor: "Alex Cole", action: "approved rule #4821", target: "PSD2 Art. 97", time: "12m ago" },
  { actor: "System", action: "auto-published 4 rules", target: "OFAC sync", time: "1h ago" },
  { actor: "Sarah Park", action: "rejected rule #4819", target: "Low confidence", time: "2h ago" },
  { actor: "Marcus Chen", action: "edited taxonomy", target: "Jurisdiction: APAC", time: "4h ago" },
  { actor: "Alex Cole", action: "invited user", target: "diana@acme.com", time: "1d ago" },
];

const Admin = () => {
  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1400px]">
      <div>
        <p className="text-xs uppercase tracking-widest text-muted-foreground">Workspace settings</p>
        <h1 className="text-3xl font-bold tracking-tight mt-1">Admin</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage users, taxonomy, and audit history.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {[
          { icon: Users, label: "Active users", value: "23" },
          { icon: Shield, label: "Roles defined", value: "4" },
          { icon: Tag, label: "Taxonomy entries", value: "187" },
        ].map((k) => (
          <div key={k.label} className="rounded-2xl glass p-5 flex items-center gap-4">
            <div className="h-10 w-10 rounded-xl bg-secondary border border-border flex items-center justify-center">
              <k.icon className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{k.label}</p>
              <p className="text-2xl font-bold">{k.value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Users */}
        <div className="lg:col-span-2 rounded-2xl glass overflow-hidden">
          <div className="p-5 border-b border-border flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">Team members</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Role-based access control (RBAC)</p>
            </div>
            <Button variant="hero" size="sm">Invite member</Button>
          </div>
          <div>
            {users.map((u) => (
              <div key={u.email} className="flex items-center gap-4 px-5 py-3.5 border-t border-border/40 hover:bg-secondary/30 transition-colors">
                <div className="h-9 w-9 rounded-full bg-gradient-primary flex items-center justify-center text-xs font-semibold text-primary-foreground shrink-0">
                  {u.initial}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{u.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                </div>
                <select defaultValue={u.role} className="text-xs h-8 px-2.5 rounded-md bg-secondary border border-border focus:outline-none">
                  <option>Admin</option>
                  <option>Reviewer</option>
                  <option>Viewer</option>
                </select>
                <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded ${
                  u.status === "active" ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
                }`}>
                  {u.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Taxonomy */}
        <div className="rounded-2xl glass p-5">
          <h2 className="text-base font-semibold mb-1">Taxonomy</h2>
          <p className="text-xs text-muted-foreground mb-4">Jurisdictions & categories</p>
          <div className="space-y-2">
            {[
              { type: "Jurisdiction", items: ["EU", "US", "UK", "APAC", "LATAM"] },
              { type: "Category", items: ["AML", "KYC", "Payments", "Sanctions"] },
              { type: "Workflow stage", items: ["Onboarding", "Monitoring", "Reporting"] },
            ].map((g) => (
              <div key={g.type} className="rounded-lg bg-secondary/40 border border-border/60 p-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-2">{g.type}</p>
                <div className="flex flex-wrap gap-1.5">
                  {g.items.map((i) => (
                    <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-secondary border border-border">{i}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Audit log */}
      <div className="rounded-2xl glass">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            <h2 className="text-base font-semibold">Audit log</h2>
          </div>
          <Button variant="outline" size="sm">Export CSV</Button>
        </div>
        <div>
          {audit.map((a, i) => (
            <div key={i} className="flex items-center gap-4 px-5 py-3 border-t border-border/40 text-sm hover:bg-secondary/20 transition-colors">
              <span className="font-medium w-32 truncate">{a.actor}</span>
              <span className="text-muted-foreground flex-1">{a.action}</span>
              <span className="text-xs font-mono text-muted-foreground hidden md:inline">{a.target}</span>
              <span className="text-xs text-muted-foreground w-20 text-right">{a.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Admin;
