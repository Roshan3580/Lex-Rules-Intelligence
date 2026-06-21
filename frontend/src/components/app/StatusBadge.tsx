import { cn } from "@/lib/utils";

const toneClasses = {
  default: "border-border bg-secondary text-muted-foreground",
  primary: "border-primary/20 bg-primary/5 text-primary",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  destructive: "border-red-200 bg-red-50 text-red-700",
  live: "border-primary/20 bg-primary/5 text-primary",
};

type StatusBadgeProps = {
  children: React.ReactNode;
  tone?: keyof typeof toneClasses;
  dot?: boolean;
  className?: string;
};

export function StatusBadge({
  children,
  tone = "default",
  dot = false,
  className,
}: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.12em]",
        toneClasses[tone],
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />}
      {children}
    </span>
  );
}
