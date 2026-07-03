import { NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001";

export const runtime = "nodejs";

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  try {
    const r = await fetch(`${BACKEND_URL}/ask`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      // 180s budget — Render free tier cold-start (~30 s) + orchestrator (~60 s worst case).
      signal: AbortSignal.timeout(180_000),
    });
    const text = await r.text();
    try {
      return NextResponse.json(JSON.parse(text), { status: r.status });
    } catch {
      return NextResponse.json({ error: text }, { status: r.status });
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "upstream-fetch-failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
