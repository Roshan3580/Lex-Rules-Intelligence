import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  Database,
  Workflow,
  CheckSquare,
  BarChart3,
  Shield,
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
import { BrandLogo } from "@/components/BrandLogo";
import { cn } from "@/lib/utils";

const items = [
  { title: "Dashboard", url: "/app", icon: LayoutDashboard },
  { title: "Rule Search", url: "/app/search", icon: Search, badge: "AI" },
  { title: "Sources", url: "/app/sources", icon: Database },
  { title: "Workflows", url: "/app/workflows", icon: Workflow },
  { title: "Review Queue", url: "/app/review", icon: CheckSquare },
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
    <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
      <div className="flex h-14 items-center border-b border-sidebar-border px-5">
        <BrandLogo showWordmark />
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-5">
        <p className="app-label px-3 pb-2">Workspace</p>
        {items.map((item) => {
          const active = isActive(item.url);
          return (
            <NavLink
              key={item.title}
              to={item.url}
              end={item.url === "/app"}
              className={cn(
                "group relative flex items-center gap-3 px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground",
              )}
            >
              {active && (
                <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 bg-primary" />
              )}
              <item.icon className={cn("h-4 w-4", active && "text-primary")} />
              <span className="flex-1">{item.title}</span>
              {item.badge && (
                <span className="border border-primary/20 bg-primary/5 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider text-primary">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="space-y-2 border-t border-sidebar-border p-3">
        <div className="border border-sidebar-border bg-sidebar-accent p-3">
          <p className="app-label mb-1">Rule intelligence</p>
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Source-backed retrieval with human-in-the-loop review.
          </p>
        </div>
        <NavLink
          to="/app/admin"
          className="flex items-center gap-3 px-3 py-2 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground"
        >
          <Settings className="h-4 w-4" />
          <span>Settings</span>
        </NavLink>
      </div>
    </aside>
  );
}
