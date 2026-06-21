import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type MetricCardProps = {
  label: string;
  value: string;
  icon?: LucideIcon;
  hint?: string;
  className?: string;
};

export function MetricCard({ label, value, icon: Icon, hint, className }: MetricCardProps) {
  return (
    <div className={cn("app-card border border-border bg-card p-5", className)}>
      {Icon && (
        <div className="mb-4 flex h-8 w-8 items-center justify-center border border-border bg-secondary">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
      )}
      <p className="font-serif text-2xl leading-none tracking-tight text-foreground sm:text-3xl">
        {value}
      </p>
      <p className="app-label mt-2">{label}</p>
      {hint && <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function MetricCardSkeleton() {
  return <div className="app-card h-28 animate-pulse border border-border bg-secondary/40 p-5" />;
}
