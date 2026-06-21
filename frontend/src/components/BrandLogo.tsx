import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

type BrandLogoProps = {
  size?: "sm" | "md" | "lg";
  showWordmark?: boolean;
  className?: string;
  theme?: "light" | "dark";
};

const sizeClasses = {
  sm: { box: "h-6 w-6 rounded-md", icon: "h-3 w-3", title: "text-xs", subtitle: "text-[9px]" },
  md: { box: "h-8 w-8 rounded-lg", icon: "h-4 w-4", title: "text-sm", subtitle: "text-[10px]" },
  lg: { box: "h-10 w-10 rounded-xl", icon: "h-5 w-5", title: "text-base", subtitle: "text-[11px]" },
};

export function BrandLogo({
  size = "md",
  showWordmark = false,
  className,
  theme = "light",
}: BrandLogoProps) {
  const s = sizeClasses[size];
  const titleColor = theme === "dark" ? "text-white" : "text-foreground";
  const subtitleColor = theme === "dark" ? "text-white/60" : "text-muted-foreground";

  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <div
        className={cn(
          s.box,
          "bg-gradient-primary flex items-center justify-center shrink-0",
        )}
      >
        <Sparkles className={cn(s.icon, "text-primary-foreground")} />
      </div>
      {showWordmark && (
        <div className="flex flex-col leading-none">
          <span className={cn(s.title, "font-semibold", titleColor)}>Lex</span>
          <span className={cn(s.subtitle, "tracking-wider uppercase", subtitleColor)}>
            Intelligence
          </span>
        </div>
      )}
    </div>
  );
}
