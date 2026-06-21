import { Bell, Search, Command } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/app/StatusBadge";
import { RbacRoleSwitcher } from "@/components/RbacRoleSwitcher";
import { getTenantId } from "@/lib/api";
import { useEffect, useState } from "react";

export function AppTopbar() {
  const [tenant, setTenant] = useState<string>(() => getTenantId());

  useEffect(() => {
    const sync = () => setTenant(getTenantId());
    window.addEventListener("rules_intel_tenant_id", sync);
    return () => window.removeEventListener("rules_intel_tenant_id", sync);
  }, []);

  return (
    <header className="sticky top-0 z-30 h-14 shrink-0 border-b border-border bg-card">
      <div className="flex h-full items-center gap-4 px-4 lg:px-6">
        <div className="relative max-w-xl flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            placeholder="Search rules, sources, workflows..."
            className="h-9 w-full border border-border bg-background pl-10 pr-20 text-sm transition-colors placeholder:text-muted-foreground focus:border-primary/40 focus:outline-none"
          />
          <kbd className="absolute right-3 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded border border-border bg-secondary px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground sm:flex">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <RbacRoleSwitcher />
          <div className="hidden items-center gap-2 border border-border bg-secondary px-2.5 py-1 md:flex">
            <span className="app-label">Tenant</span>
            <span className="font-mono text-[11px] text-foreground">{tenant}</span>
          </div>
          <StatusBadge tone="success" dot className="hidden md:inline-flex">
            Live demo
          </StatusBadge>
          <Button variant="ghost" size="icon" className="relative h-9 w-9">
            <Bell className="h-4 w-4" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
          </Button>
          <div className="flex h-8 w-8 items-center justify-center bg-primary text-[11px] font-semibold text-primary-foreground">
            AC
          </div>
        </div>
      </div>
    </header>
  );
}
