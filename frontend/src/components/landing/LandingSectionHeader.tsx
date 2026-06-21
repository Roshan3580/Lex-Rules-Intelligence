type LandingSectionHeaderProps = {
  label: string;
  title: string;
  description?: string;
  align?: "left" | "center";
};

export function LandingSectionHeader({
  label,
  title,
  description,
  align = "left",
}: LandingSectionHeaderProps) {
  return (
    <div className={align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-2xl"}>
      <p className="landing-label mb-4">{label}</p>
      <h2 className="font-serif text-3xl leading-[1.1] tracking-tight text-[hsl(var(--landing-fg))] md:text-5xl">
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-base leading-relaxed text-[hsl(var(--landing-muted))] md:text-lg">
          {description}
        </p>
      )}
    </div>
  );
}
