import { cn } from "@/lib/utils";

type EmptyStateProps = {
  title?: string;
  description: string;
  className?: string;
  action?: React.ReactNode;
};

export function EmptyState({ title, description, className, action }: EmptyStateProps) {
  return (
    <div className={cn("py-8 text-center", className)}>
      {title && <p className="text-sm font-medium text-foreground">{title}</p>}
      <p className={cn("text-sm text-muted-foreground", title && "mt-1")}>{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
