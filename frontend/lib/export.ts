/**
 * Tiny client-side export helpers for the demo.
 *
 * Kept intentionally small — no full-blown data-transform layer, no CSV parser
 * dependency. If we ever need to handle multi-line strings inside cells, swap
 * this for papaparse's unparse; until then, a two-quote-escape is enough.
 */

type Row = Record<string, unknown>;

/** RFC-4180-style CSV: double-up embedded quotes, wrap fields with commas or newlines. */
export function rowsToCsv(rows: Row[]): string {
  if (!rows.length) return "";
  const cols = Object.keys(rows[0] as Row);
  const esc = (v: unknown): string => {
    if (v === null || v === undefined) return "";
    const s = typeof v === "object" ? JSON.stringify(v) : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = cols.join(",");
  const body = rows.map((r) => cols.map((c) => esc(r[c])).join(",")).join("\n");
  return `${header}\n${body}`;
}

export function downloadBlob(content: BlobPart, filename: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Lazy-imported html-to-image; SSR-safe. */
export async function downloadElementAsPng(el: HTMLElement | null, filename: string): Promise<void> {
  if (!el) return;
  const { toPng } = await import("html-to-image");
  const dataUrl = await toPng(el, { backgroundColor: "#09090b", pixelRatio: 2 });
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/**
 * Turn raw Postgres / composer error strings into a short one-liner the user
 * can act on. Falls back to the raw error if no pattern matches.
 */
export function schemaHint(rawError: string): string | null {
  const err = rawError.toLowerCase();
  if (err.includes("column") && err.includes("does not exist")) {
    // Extract "column X does not exist" so we can name the offender.
    const m = /column\s+"?([\w.]+)"?\s+does not exist/i.exec(rawError);
    const col = m?.[1] ?? "that column";
    return `Hint: ${col} isn't in the schema — the composer hallucinated a column name. Try rephrasing with the actual column (e.g. firstname/lastname instead of customername).`;
  }
  if (err.includes("statement timeout")) {
    return "Hint: the query took longer than 30 s to execute. Add a year/quarter filter or a LIMIT to narrow the scan.";
  }
  if (err.includes("missing from-clause entry")) {
    return "Hint: the composer used a table alias without declaring it. This is a gpt-4o-mini flake — one retry usually fixes it (or upgrade to a larger backbone).";
  }
  if (err.includes("empty sql produced by composer")) {
    return "Hint: composer bailed after 2 attempts. This query pattern (multi-fact UNION) is a known limit of gpt-4o-mini — see test_case_matrix.md.";
  }
  if (err.includes("connection timeout")) {
    return "Hint: the Postgres container may be paused. Check `docker ps` and start scm-postgres if needed.";
  }
  return null;
}
