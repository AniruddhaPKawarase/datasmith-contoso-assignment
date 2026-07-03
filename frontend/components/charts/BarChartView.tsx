"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Row = Record<string, unknown>;

type Props = {
  rows: Row[];
  x: string;
  y: string;
  series?: string | null;
  title?: string;
};

const COLORS = ["#10b981", "#60a5fa", "#f59e0b", "#f472b6", "#a78bfa", "#f87171", "#34d399"];

export function BarChartView({ rows, x, y, series, title }: Props) {
  const data = series ? pivot(rows, x, y, series) : rows;
  const seriesKeys = series ? Array.from(new Set(rows.map((r) => String(r[series])))) : [y];

  // If we have >20 categories we truncate to top 20 by y-value for readability.
  const trimmed =
    (data as Row[]).length > 20 && !series
      ? (data as Row[]).slice().sort((a, b) => Number(b[y] ?? 0) - Number(a[y] ?? 0)).slice(0, 20)
      : data;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
      {title && <div className="mb-2 text-xs text-zinc-400">{title}</div>}
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={trimmed as unknown as Row[]} margin={{ top: 10, right: 20, bottom: 40, left: 0 }}>
          <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
          <XAxis
            dataKey={x}
            stroke="#a1a1aa"
            fontSize={11}
            angle={-30}
            textAnchor="end"
            interval={0}
          />
          <YAxis stroke="#a1a1aa" fontSize={11} />
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", fontSize: 12 }}
            labelStyle={{ color: "#e4e4e7" }}
          />
          {series && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {seriesKeys.map((k, i) => (
            <Bar
              key={k}
              dataKey={k}
              fill={COLORS[i % COLORS.length]}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function pivot(rows: Row[], x: string, y: string, series: string): Row[] {
  const byX = new Map<unknown, Row>();
  for (const r of rows) {
    const xv = r[x];
    const sv = String(r[series]);
    if (!byX.has(xv)) byX.set(xv, { [x]: xv });
    (byX.get(xv) as Row)[sv] = r[y];
  }
  return Array.from(byX.values());
}
