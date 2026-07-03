"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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

// Dim palette that reads well on dark background.
const COLORS = ["#10b981", "#60a5fa", "#f59e0b", "#f472b6", "#a78bfa", "#f87171", "#34d399"];

/**
 * If a series column is set we pivot rows into {x, series_a: y, series_b: y, ...}.
 * Otherwise we plot a single y line.
 */
export function LineChartView({ rows, x, y, series, title }: Props) {
  const data = series ? pivot(rows, x, y, series) : rows;
  const seriesKeys = series ? Array.from(new Set(rows.map((r) => String(r[series])))) : [y];

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
      {title && <div className="mb-2 text-xs text-zinc-400">{title}</div>}
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data as unknown as Row[]} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
          <XAxis dataKey={x} stroke="#a1a1aa" fontSize={11} />
          <YAxis stroke="#a1a1aa" fontSize={11} />
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", fontSize: 12 }}
            labelStyle={{ color: "#e4e4e7" }}
          />
          {series && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {seriesKeys.map((k, i) => (
            <Line
              key={k}
              type="monotone"
              dataKey={k}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function pivot(rows: Row[], x: string, y: string, series: string): Row[] {
  const byX = new Map<unknown, Row>();
  for (const r of rows) {
    const xv = r[x];
    const sv = String(r[series]);
    const yv = r[y];
    if (!byX.has(xv)) byX.set(xv, { [x]: xv });
    (byX.get(xv) as Row)[sv] = yv;
  }
  return Array.from(byX.values());
}
