import { AlertCircle, CheckCircle2, HelpCircle, OctagonAlert } from "lucide-react";

const STATUS_CONFIG = {
  healthy: { color: "var(--status-good)", label: "Healthy", Icon: CheckCircle2 },
  warning: { color: "var(--status-warning)", label: "Warning", Icon: AlertCircle },
  critical: { color: "var(--status-critical)", label: "Critical", Icon: OctagonAlert },
  no_data: { color: "var(--text-muted)", label: "No data", Icon: HelpCircle },
} as const;

export function StatusBadge({ status, size = "sm" }: { status: keyof typeof STATUS_CONFIG; size?: "sm" | "md" }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.no_data;
  const iconSize = size === "sm" ? 13 : 15;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ background: "color-mix(in srgb, " + cfg.color + " 16%, transparent)", color: cfg.color }}
    >
      <cfg.Icon size={iconSize} />
      {cfg.label}
    </span>
  );
}

export function StatusDot({ status }: { status: keyof typeof STATUS_CONFIG }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.no_data;
  return <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: cfg.color }} />;
}
