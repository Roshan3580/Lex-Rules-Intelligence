import { cn } from "@/lib/utils";

interface ConfidenceProps {
  value: number; // 0-100
  showLabel?: boolean;
  size?: "sm" | "md";
}

export function Confidence({ value, showLabel = true, size = "md" }: ConfidenceProps) {
  const tone =
    value >= 85 ? "success" : value >= 65 ? "teal" : value >= 45 ? "warning" : "destructive";
  const colorClass = {
    success: "bg-success",
    teal: "bg-teal",
    warning: "bg-warning",
    destructive: "bg-destructive",
  }[tone];
  const textClass = {
    success: "text-success",
    teal: "text-teal",
    warning: "text-warning",
    destructive: "text-destructive",
  }[tone];

  return (
    <div className="flex items-center gap-2">
      <div className={cn("rounded-full bg-secondary overflow-hidden", size === "sm" ? "h-1 w-16" : "h-1.5 w-24")}>
        <div className={cn("h-full transition-all", colorClass)} style={{ width: `${value}%` }} />
      </div>
      {showLabel && (
        <span className={cn("font-mono font-medium", textClass, size === "sm" ? "text-[10px]" : "text-xs")}>
          {value}%
        </span>
      )}
    </div>
  );
}
