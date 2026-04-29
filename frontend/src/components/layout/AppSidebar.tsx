import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  Database,
  Workflow,
  CheckSquare,
  BarChart3,
  Shield,
  Sparkles,
  Settings,
  ClipboardCheck,
  Inbox,
  Route,
  GitBranch,
  TriangleAlert,
  ClipboardList,
  PartyPopper,
  ScrollText,
  Webhook,
} from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { title: "Dashboard", url: "/app", icon: LayoutDashboard },
  { title: "Rule Search", url: "/app/search", icon: Search, badge: "AI" },
  { title: "Sources", url: "/app/sources", icon: Database },
  { title: "Workflows", url: "/app/workflows", icon: Workflow },
  { title: "Review Queue", url: "/app/review", icon: CheckSquare, count: 12 },
  { title: "Submission Validator", url: "/app/validate", icon: ClipboardCheck },
  { title: "Outcomes", url: "/app/outcomes", icon: Inbox },
  { title: "Submission path", url: "/app/submission", icon: Route },
  { title: "Workflow runner", url: "/app/workflow-runner", icon: GitBranch },
  { title: "Rejections", url: "/app/rejections", icon: TriangleAlert },
  { title: "Onboarding", url: "/app/onboarding", icon: ClipboardList },
  { title: "Guided demo", url: "/app/demo", icon: PartyPopper },
  { title: "Webhooks", url: "/app/webhooks", icon: Webhook },
  { title: "Audit Trail", url: "/app/audit", icon: ScrollText },
  { title: "Analytics", url: "/app/analytics", icon: BarChart3 },
  { title: "Admin", url: "/app/admin", icon: Shield },
];

export function AppSidebar() {
  const location = useLocation();
  const isActive = (path: string) =>
    path === "/app" ? location.pathname === "/app" : location.pathname.startsWith(path);

  return (
    <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar/80 backdrop-blur-xl">
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-sidebar-border">
        <div className="h-8 w-8 rounded-lg bg-gradient-primary flex items-center justify-center shadow-glow">
          <Sparkles className="h-4 w-4 text-primary-foreground" />
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-sm font-semibold text-foreground">Lex</span>
          <span className="text-[10px] text-muted-foreground tracking-wider uppercase">Intelligence</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-5 space-y-0.5 overflow-y-auto">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
          Workspace
        </p>
        {items.map((item) => {
          const active = isActive(item.url);
          return (
            <NavLink
              key={item.title}
              to={item.url}
              end={item.url === "/app"}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all",
                active
                  ? "bg-sidebar-accent text-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
              )}
            >
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r bg-gradient-primary" />
              )}
              <item.icon className={cn("h-4 w-4", active && "text-primary")} />
              <span className="flex-1">{item.title}</span>
              {item.badge && (
                <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gradient-primary text-primary-foreground">
                  {item.badge}
                </span>
              )}
              {item.count && (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-warning/15 text-warning">
                  {item.count}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="p-3 border-t border-sidebar-border space-y-2">
        <div className="rounded-xl p-3 bg-gradient-to-br from-primary/10 to-accent/10 border border-primary/20">
          <p className="text-xs font-semibold text-foreground">Pro plan</p>
          <p className="text-[11px] text-muted-foreground mt-0.5">82% of monthly extractions used</p>
          <div className="mt-2 h-1 rounded-full bg-secondary overflow-hidden">
            <div className="h-full w-[82%] bg-gradient-primary" />
          </div>
        </div>
        <NavLink
          to="/app/admin"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-foreground transition-all"
        >
          <Settings className="h-4 w-4" />
          <span>Settings</span>
        </NavLink>
      </div>
    </aside>
  );
}
