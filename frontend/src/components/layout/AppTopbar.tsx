import { Bell, Search, Command } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RbacRoleSwitcher } from "@/components/RbacRoleSwitcher";

export function AppTopbar() {
  return (
    <header className="h-16 shrink-0 border-b border-border bg-background/60 backdrop-blur-xl sticky top-0 z-30">
      <div className="h-full px-4 lg:px-6 flex items-center gap-4">
        <div className="relative flex-1 max-w-xl">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            placeholder="Search rules, sources, workflows..."
            className="w-full h-10 pl-10 pr-20 rounded-lg bg-secondary/60 border border-border/60 text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/40 focus:bg-secondary transition-all"
          />
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-1 text-[10px] text-muted-foreground bg-background/80 border border-border px-1.5 py-0.5 rounded font-mono">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <RbacRoleSwitcher />
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-success/10 border border-success/20">
            <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
            <span className="text-[11px] font-medium text-success">All systems operational</span>
          </div>
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-4 w-4" />
            <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-primary" />
          </Button>
          <div className="h-9 w-9 rounded-full bg-gradient-primary flex items-center justify-center text-xs font-semibold text-primary-foreground shadow-glow">
            AC
          </div>
        </div>
      </div>
    </header>
  );
}
