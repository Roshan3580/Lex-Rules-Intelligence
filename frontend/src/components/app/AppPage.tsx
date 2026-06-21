import { cn } from "@/lib/utils";

type AppPageProps = {
  children: React.ReactNode;
  className?: string;
  narrow?: boolean;
};

export function AppPage({ children, className, narrow }: AppPageProps) {
  return (
    <div
      className={cn(
        "app-page p-6 lg:p-8 space-y-6",
        narrow ? "max-w-5xl mx-auto" : "max-w-[1600px]",
        className,
      )}
    >
      {children}
    </div>
  );
}
