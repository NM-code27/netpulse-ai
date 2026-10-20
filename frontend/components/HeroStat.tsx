import type { LucideIcon } from "lucide-react";

export function HeroStat({
  label, value, hint, icon: Icon, color = "var(--accent)", bg = "var(--accent-soft)",
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon: LucideIcon;
  color?: string;
  bg?: string;
}) {
  return (
    <div
      className="group relative flex-1 overflow-hidden rounded-2xl border p-5 transition-all duration-300 hover:-translate-y-0.5"
      style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-sm)" }}
    >
      <div
        className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-60 transition-transform duration-500 group-hover:scale-125"
        style={{ background: bg }}
      />
      <div className="relative flex items-start justify-between">
        <div>
          <div className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
            {label}
          </div>
          <div className="mt-2 text-3xl font-bold tabular" style={{ color: "var(--text-primary)" }}>
            {value}
          </div>
          {hint && (
            <div className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
              {hint}
            </div>
          )}
        </div>
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
          style={{ background: bg }}
        >
          <Icon size={18} color={color} />
        </div>
      </div>
    </div>
  );
}
