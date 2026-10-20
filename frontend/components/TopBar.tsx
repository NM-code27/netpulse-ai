"use client";

import { useEffect, useState } from "react";

export function TopBar({ title, subtitle }: { title: string; subtitle?: string }) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <header
      className="sticky top-0 z-10 flex items-center justify-between border-b px-6 py-4 backdrop-blur"
      style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.85)" }}
    >
      <div>
        <h1 className="text-lg font-bold tracking-tight">{title}</h1>
        {subtitle && (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {subtitle}
          </p>
        )}
      </div>
      <div
        className="flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium tabular"
        style={{ borderColor: "var(--border)", color: "var(--text-secondary)", background: "var(--surface)" }}
      >
        <span className="relative inline-flex h-2 w-2">
          <span
            className="absolute inline-flex h-full w-full rounded-full"
            style={{ background: "var(--status-good)", animation: "pulse-ring 1.6s cubic-bezier(0,0,0.2,1) infinite" }}
          />
          <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: "var(--status-good)" }} />
        </span>
        Live
        {now && <span style={{ color: "var(--text-muted)" }}>&middot; {now.toLocaleTimeString()}</span>}
      </div>
    </header>
  );
}
