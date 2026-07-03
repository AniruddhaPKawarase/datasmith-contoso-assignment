"use client";

import { CheckCircle2, AlertTriangle, HelpCircle, Database, Clock, Coins, Copy, Download, ImageDown } from "lucide-react";
import { useRef, useState } from "react";
import type { Turn, VizFormat, Panel } from "@/lib/types";
import { LineChartView } from "@/components/charts/LineChartView";
import { BarChartView } from "@/components/charts/BarChartView";
import { PieChartView } from "@/components/charts/PieChartView";
import { KpiCard } from "@/components/charts/KpiCard";
import { downloadBlob, downloadElementAsPng, rowsToCsv, schemaHint } from "@/lib/export";

type Props = {
  turn: Turn;
};

export function TurnView({ turn }: Props) {
  return (
    <article className="space-y-4">
      {/* User query */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-xl rounded-tr-sm bg-emerald-700/30 px-4 py-2.5 text-sm text-emerald-50">
          {turn.query}
        </div>
      </div>

      {/* Loading state */}
      {!turn.response && !turn.error && (
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
          Thinking…
        </div>
      )}

      {/* Error */}
      {turn.error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-700 bg-red-950 p-3 text-sm text-red-200">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Request failed</p>
            <p className="mt-1 text-xs text-red-300">{turn.error}</p>
          </div>
        </div>
      )}

      {/* Response */}
      {turn.response && <ResponseBody response={turn.response} />}
    </article>
  );
}

function ResponseBody({ response }: { response: Turn["response"] }) {
  if (!response) return null;

  // Clarification path
  if (response.intent === "clarification_needed" || response.clarification_question) {
    return (
      <div className="rounded-xl rounded-tl-sm border border-amber-700 bg-amber-950/40 p-4 text-sm text-amber-100">
        <div className="mb-2 flex items-center gap-2 text-amber-300">
          <HelpCircle size={16} />
          <span className="text-xs font-medium uppercase tracking-wide">Clarification needed</span>
        </div>
        <p>{response.clarification_question ?? "Please provide more detail."}</p>
      </div>
    );
  }

  // Out-of-scope path
  if (response.intent === "out_of_scope") {
    return (
      <div className="rounded-xl rounded-tl-sm border border-zinc-700 bg-zinc-900 p-4 text-sm text-zinc-300">
        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Out of scope</p>
        <p className="mt-1">This question doesn&apos;t match an SCM domain I can answer.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header chips */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-full bg-zinc-800 px-2.5 py-0.5 text-zinc-300">
          intent: <span className="font-mono text-emerald-300">{response.intent}</span>
        </span>
        {response.domains.length > 0 && (
          <span className="rounded-full bg-zinc-800 px-2.5 py-0.5 text-zinc-300">
            domains: <span className="font-mono text-emerald-300">{response.domains.join(", ")}</span>
          </span>
        )}
        <span className="flex items-center gap-1 rounded-full bg-zinc-800 px-2.5 py-0.5 text-zinc-300">
          <Clock size={11} /> {response.latency_ms} ms
        </span>
        <span className="flex items-center gap-1 rounded-full bg-zinc-800 px-2.5 py-0.5 text-zinc-300">
          <Coins size={11} /> ${response.estimated_cost_usd.toFixed(4)}
        </span>
        {response.row_count > 0 && (
          <span className="flex items-center gap-1 rounded-full bg-zinc-800 px-2.5 py-0.5 text-zinc-300">
            <Database size={11} /> {response.row_count} rows
          </span>
        )}
      </div>

      {/* SQL block — collapsed by default (details/summary) */}
      {response.sql && <SqlBlock sql={response.sql} explainOk={response.explain_ok} />}

      {/* Visualization — chart / kpi / table / mixed / prose */}
      {response.visualization && response.rows && response.rows.length > 0 && (
        <VisualizationView
          fmt={response.visualization.format as VizFormat}
          rows={response.rows}
          x={response.visualization.x_axis}
          y={response.visualization.y_axis}
          series={response.visualization.series}
          title={response.visualization.title}
          reasoning={response.visualization.reasoning}
        />
      )}
      {response.rows && response.rows.length === 0 && response.explain_ok && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-xs text-zinc-400">
          Query executed successfully — 0 rows returned.
        </div>
      )}

      {/* Multi-step panels — TC06 funnel, TC08 multi-panel */}
      {response.panels && response.panels.length > 0 && (
        <div className="space-y-4">
          {response.panels.map((panel) => (
            <PanelBlock key={panel.step} panel={panel} />
          ))}
        </div>
      )}

      {/* Agent trace — Bonus B2 Planner+Executor handoff log */}
      {response.trace && (response.trace.plan_steps.length > 0 || response.trace.executor_notes) && (
        <details className="rounded-xl border border-zinc-800 bg-zinc-950">
          <summary className="cursor-pointer border-b border-zinc-800 px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500 hover:text-zinc-300">
            Agent Trace
          </summary>
          <div className="p-3 text-xs text-zinc-300 space-y-2">
            <div>
              <span className="font-mono text-emerald-400">Planner →</span>{" "}
              intent=<span className="font-mono">{response.trace.planner_intent}</span>{" "}
              domains=[<span className="font-mono">{response.trace.planner_domains.join(", ")}</span>]
            </div>
            {response.trace.plan_steps.length > 0 && (
              <ol className="ml-4 space-y-1 list-decimal text-[11px]">
                {response.trace.plan_steps.map((s) => (
                  <li key={s.step}>
                    <span className="font-mono text-emerald-300">{s.name}</span> — {s.natural_language}
                    {s.rationale && <span className="text-zinc-500 italic"> · {s.rationale}</span>}
                  </li>
                ))}
              </ol>
            )}
            <div className="text-zinc-500 italic">
              <span className="font-mono text-emerald-400">Executor →</span> {response.trace.executor_notes}
            </div>
          </div>
        </details>
      )}

      {/* Error inline — with schema-aware hint */}
      {response.error && <ErrorInline raw={response.error} />}

      {/* Token breakdown */}
      <div className="flex flex-wrap gap-3 text-[10px] text-zinc-500">
        <span>router: {response.token_usage.router}t</span>
        <span>sql_gen: {response.token_usage.sql_gen}t</span>
        <span>validator: {response.token_usage.validator}t</span>
      </div>
    </div>
  );
}


function VisualizationView({
  fmt,
  rows,
  x,
  y,
  series,
  title,
  reasoning,
}: {
  fmt: VizFormat;
  rows: Record<string, unknown>[];
  x: string | null;
  y: string | null;
  series: string | null;
  title: string;
  reasoning: string;
}) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const badge = (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-emerald-950/40 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-emerald-300">
          {fmt}
        </span>
        {reasoning && <span className="text-[10px] text-zinc-500 italic">{reasoning}</span>}
      </div>
      <ExportActions rows={rows} chartRef={chartRef} chartExportable={fmt !== "prose"} />
    </div>
  );

  const numericCol = () => {
    const first = rows[0] ?? {};
    return y ?? Object.keys(first).find((k) => typeof first[k] === "number") ?? "";
  };

  if (fmt === "kpi") {
    return (
      <div className="space-y-2">
        {badge}
        <div ref={chartRef}><KpiCard rows={rows} y={y} title={title} /></div>
      </div>
    );
  }
  if (fmt === "line" && x) {
    return (
      <div className="space-y-2">
        {badge}
        <div ref={chartRef}><LineChartView rows={rows} x={x} y={numericCol()} series={series} title={title} /></div>
      </div>
    );
  }
  if (fmt === "bar" && x) {
    return (
      <div className="space-y-2">
        {badge}
        <div ref={chartRef}><BarChartView rows={rows} x={x} y={numericCol()} series={series} title={title} /></div>
      </div>
    );
  }
  if (fmt === "pie" && x) {
    return (
      <div className="space-y-2">
        {badge}
        <div ref={chartRef}><PieChartView rows={rows} x={x} y={numericCol()} title={title} /></div>
      </div>
    );
  }
  if (fmt === "mixed" && x) {
    return (
      <div className="space-y-3">
        {badge}
        <div ref={chartRef}><BarChartView rows={rows} x={x} y={numericCol()} series={series} title={title} /></div>
        <ResultTable rows={rows} />
      </div>
    );
  }
  // "prose" or fallback → table only (no PNG button)
  return (
    <div className="space-y-2">
      {badge}
      <ResultTable rows={rows} />
    </div>
  );
}


function ExportActions({
  rows,
  chartRef,
  chartExportable,
}: {
  rows: Record<string, unknown>[];
  chartRef: React.RefObject<HTMLDivElement | null>;
  chartExportable: boolean;
}) {
  const [busy, setBusy] = useState<"png" | null>(null);
  if (!rows.length) return null;
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);

  const btn = "inline-flex items-center gap-1 rounded border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-[10px] text-zinc-400 hover:border-emerald-700 hover:text-emerald-300 disabled:opacity-50";

  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        className={btn}
        onClick={() => downloadBlob(rowsToCsv(rows), `contoso-result-${ts}.csv`, "text/csv;charset=utf-8")}
        title="Download rows as CSV"
      >
        <Download size={11} /> CSV
      </button>
      {chartExportable && (
        <button
          type="button"
          disabled={busy === "png"}
          className={btn}
          onClick={async () => {
            setBusy("png");
            try {
              await downloadElementAsPng(chartRef.current, `contoso-chart-${ts}.png`);
            } finally {
              setBusy(null);
            }
          }}
          title="Download chart as PNG"
        >
          <ImageDown size={11} /> {busy === "png" ? "…" : "PNG"}
        </button>
      )}
    </div>
  );
}


function SqlBlock({ sql, explainOk }: { sql: string; explainOk: boolean }) {
  const [copied, setCopied] = useState(false);
  return (
    <details className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950" open>
      <summary className="flex cursor-pointer items-center justify-between border-b border-zinc-800 bg-zinc-900 px-3 py-1.5 list-none [&::-webkit-details-marker]:hidden">
        <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
          Generated SQL
        </span>
        <div className="flex items-center gap-2">
          {explainOk && (
            <span className="flex items-center gap-1 text-[10px] text-emerald-400">
              <CheckCircle2 size={11} /> EXPLAIN OK
            </span>
          )}
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded border border-zinc-800 bg-zinc-950 px-2 py-0.5 text-[10px] text-zinc-400 hover:border-emerald-700 hover:text-emerald-300"
            onClick={async (e) => {
              e.preventDefault();
              try {
                await navigator.clipboard.writeText(sql);
                setCopied(true);
                setTimeout(() => setCopied(false), 1200);
              } catch { /* ignore clipboard rejection in insecure ctx */ }
            }}
            title="Copy SQL to clipboard"
          >
            <Copy size={11} /> {copied ? "copied" : "copy"}
          </button>
        </div>
      </summary>
      <pre className="overflow-x-auto p-3 text-xs leading-relaxed text-zinc-200">
        <code>{sql}</code>
      </pre>
    </details>
  );
}


function ErrorInline({ raw }: { raw: string }) {
  const hint = schemaHint(raw);
  return (
    <div className="rounded-lg border border-amber-800 bg-amber-950/40 p-3 text-xs text-amber-200 space-y-1">
      <div>Execution: {raw}</div>
      {hint && <div className="text-amber-300/80 italic">{hint}</div>}
    </div>
  );
}


function ResultTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return null;
  const first = rows[0] ?? {};
  const columns = Object.keys(first);
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
      <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900 px-3 py-1.5">
        <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
          Result · {rows.length} row{rows.length === 1 ? "" : "s"}
        </span>
      </header>
      <div className="max-h-96 overflow-auto">
        <table className="min-w-full text-xs">
          <thead className="sticky top-0 bg-zinc-900/95">
            <tr>
              {columns.map((c) => (
                <th
                  key={c}
                  className="border-b border-zinc-800 px-3 py-2 text-left font-medium text-emerald-300"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? "bg-zinc-950" : "bg-zinc-900/30"}>
                {columns.map((c) => (
                  <td
                    key={c}
                    className="border-b border-zinc-900 px-3 py-2 align-top text-zinc-200"
                  >
                    {formatCell(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    return Number.isInteger(v) ? v.toLocaleString() : v.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}


function PanelBlock({ panel }: { panel: Panel }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-700 text-[10px] font-bold text-white">
            {panel.step}
          </span>
          <span className="text-xs font-medium text-zinc-200">{panel.name}</span>
        </div>
        <span className="text-[10px] text-zinc-500">{panel.row_count} row{panel.row_count === 1 ? "" : "s"}</span>
      </div>
      {panel.sql && (
        <details className="rounded-lg border border-zinc-800 bg-zinc-950">
          <summary className="cursor-pointer px-2 py-1 text-[10px] uppercase tracking-wider text-zinc-500 hover:text-zinc-300">
            SQL
          </summary>
          <pre className="overflow-x-auto p-2 text-[11px] leading-relaxed text-zinc-200"><code>{panel.sql}</code></pre>
        </details>
      )}
      {panel.visualization && panel.rows && panel.rows.length > 0 && (
        <VisualizationView
          fmt={panel.visualization.format as VizFormat}
          rows={panel.rows}
          x={panel.visualization.x_axis}
          y={panel.visualization.y_axis}
          series={panel.visualization.series}
          title={panel.visualization.title}
          reasoning={panel.visualization.reasoning}
        />
      )}
      {panel.error && (
        <div className="text-xs text-amber-200">error: {panel.error}</div>
      )}
    </div>
  );
}
