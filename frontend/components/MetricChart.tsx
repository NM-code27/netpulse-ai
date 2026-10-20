"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from "recharts";
import type { MetricPoint } from "@/lib/types";

function fmtTime(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function MetricChart({
  title, unit, points, color = "var(--series-blue)", threshold,
}: { title: string; unit: string; points: MetricPoint[]; color?: string; threshold?: number }) {
  const data = points.map((p) => ({ t: p.timestamp, v: p.value }));
  const gradientId = `grad-${title.replace(/\s+/g, "-")}`;

  return (
    <div
      className="animate-fade-up rounded-2xl border p-4 transition-shadow hover:shadow-md"
      style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-sm)" }}
    >
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>
          {title}
        </span>
        <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
          {unit}
        </span>
      </div>
      <div style={{ width: "100%", height: 140 }}>
        {data.length > 1 ? (
          <ResponsiveContainer>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="t"
                tickFormatter={fmtTime}
                stroke="var(--baseline)"
                tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                minTickGap={40}
                axisLine={{ stroke: "var(--gridline)" }}
                tickLine={false}
              />
              <YAxis
                stroke="var(--baseline)"
                tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                width={44}
                domain={["auto", "auto"]}
                axisLine={false}
                tickLine={false}
              />
              {threshold !== undefined && (
                <ReferenceLine y={threshold} stroke="var(--status-critical)" strokeDasharray="4 4" strokeOpacity={0.6} />
              )}
              <Tooltip
                labelFormatter={(v) => fmtTime(String(v))}
                contentStyle={{
                  background: "var(--surface)", border: "1px solid var(--border)",
                  borderRadius: 10, fontSize: 12, boxShadow: "var(--shadow-md)",
                }}
                labelStyle={{ color: "var(--text-muted)" }}
              />
              <Area
                type="monotone" dataKey="v"
                stroke={color} strokeWidth={2.25}
                fill={`url(#${gradientId})`}
                dot={false} isAnimationActive={true} animationDuration={600}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-xs" style={{ color: "var(--text-muted)" }}>
            Waiting for data...
          </div>
        )}
      </div>
    </div>
  );
}
