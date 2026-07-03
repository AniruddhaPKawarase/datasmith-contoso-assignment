"use client";

type Row = Record<string, unknown>;

type Props = {
  rows: Row[];
  y?: string | null;
  title?: string;
};

export function KpiCard({ rows, y, title }: Props) {
  const row = rows[0] ?? {};
  const key = y && y in row ? y : Object.keys(row)[0];
  const raw = key ? row[key] : null;
  const formatted =
    typeof raw === "number"
      ? Number.isInteger(raw)
        ? raw.toLocaleString()
        : raw.toLocaleString(undefined, { maximumFractionDigits: 2 })
      : String(raw ?? "—");

  return (
    <div className="rounded-xl border border-emerald-700/50 bg-emerald-950/20 p-6 text-center">
      {title && <div className="mb-2 text-xs uppercase tracking-wider text-emerald-300">{title}</div>}
      <div className="text-4xl font-semibold text-emerald-100">{formatted}</div>
      {key && <div className="mt-2 text-[10px] uppercase tracking-widest text-emerald-400/70">{key}</div>}
    </div>
  );
}
