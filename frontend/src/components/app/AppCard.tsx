import { cn } from "@/lib/utils";

type AppCardProps = {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
};

const paddingClasses = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export function AppCard({ children, className, padding = "md" }: AppCardProps) {
  return (
    <div className={cn("app-card border border-border bg-card", paddingClasses[padding], className)}>
      {children}
    </div>
  );
}

type AppCardHeaderProps = {
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
};

export function AppCardHeader({ title, description, action, className }: AppCardHeaderProps) {
  return (
    <div className={cn("mb-5 flex items-start justify-between gap-3", className)}>
      <div>
        <h2 className="text-sm font-medium text-foreground">{title}</h2>
        {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}
