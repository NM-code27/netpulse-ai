"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, AlertTriangle, FlaskConical, Globe2, LayoutDashboard } from "lucide-react";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/evaluation", label: "Model Evaluation", icon: FlaskConical },
  { href: "/realworld", label: "Real-World Data", icon: Globe2 },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="hidden md:flex w-64 shrink-0 flex-col border-r px-4 py-5"
      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
    >
      <div className="flex items-center gap-2.5 px-2 pb-6">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-xl"
          style={{ background: "var(--accent-gradient)", boxShadow: "0 4px 14px -4px rgba(42,110,224,0.5)" }}
        >
          <Activity size={18} color="white" strokeWidth={2.5} />
        </div>
        <div>
          <div className="text-sm font-bold leading-tight">NetPulse AI</div>
          <div className="text-[11px] leading-tight" style={{ color: "var(--text-muted)" }}>
            Predictive Network Ops
          </div>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className="relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
              style={{
                background: active ? "var(--accent-soft)" : "transparent",
                color: active ? "var(--accent-strong)" : "var(--text-secondary)",
              }}
            >
              {active && (
                <span
                  className="absolute left-0 top-1/2 h-4 w-1 -translate-y-1/2 rounded-full"
                  style={{ background: "var(--accent)" }}
                />
              )}
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
