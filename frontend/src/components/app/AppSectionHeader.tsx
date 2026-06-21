import { cn } from "@/lib/utils";

type AppSectionHeaderProps = {
  label?: string;
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  titleClassName?: string;
};

export function AppSectionHeader({
  label,
  title,
  description,
  actions,
  className,
  titleClassName,
}: AppSectionHeaderProps) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div>
        {label && <p className="app-label mb-2">{label}</p>}
        <h1
          className={cn(
            "font-serif text-3xl leading-tight tracking-tight text-foreground md:text-4xl",
            titleClassName,
          )}
        >
          {title}
        </h1>
        {description && (
          <div className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</div>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
