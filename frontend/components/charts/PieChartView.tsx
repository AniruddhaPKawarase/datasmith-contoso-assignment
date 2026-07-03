"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

type Row = Record<string, unknown>;

type Props = {
  rows: Row[];
  x: string;  // category label
  y: string;  // numeric value
  title?: string;
};

const COLORS = ["#10b981", "#60a5fa", "#f59e0b", "#f472b6", "#a78bfa", "#f87171", "#34d399", "#facc15"];

export function PieChartView({ rows, x, y, title }: Props) {
  const data = rows
    .map((r) => ({ name: String(r[x]), value: Number(r[y] ?? 0) }))
    .filter((d) => d.value > 0);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
      {title && <div className="mb-2 text-xs text-zinc-400">{title}</div>}
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" outerRadius={100} isAnimationActive={false}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
