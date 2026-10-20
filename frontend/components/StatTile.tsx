export function StatTile({
  label, value, hint, accent,
}: { label: string; value: string | number; hint?: string; accent?: string }) {
  return (
    <div
      className="flex-1 rounded-2xl border p-5 transition-shadow hover:shadow-md"
      style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-sm)" }}
    >
      <div className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
      <div
        className="mt-1.5 text-3xl font-bold tabular"
        style={{ color: accent || "var(--text-primary)" }}
      >
        {value}
      </div>
      {hint && (
        <div className="mt-0.5 text-xs" style={{ color: "var(--text-secondary)" }}>
          {hint}
        </div>
      )}
    </div>
  );
}
