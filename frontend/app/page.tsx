"use client";

import { useEffect, useRef, useState } from "react";
import { ChatInput } from "@/components/ChatInput";
import { Sidebar } from "@/components/Sidebar";
import { TurnView } from "@/components/TurnView";
import type { AskResponse, Turn } from "@/lib/types";

function uid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export default function Page() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sessionId, setSessionId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Generate session_id on the client to avoid hydration mismatch.
    setSessionId(uid());
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  async function handleSend(query: string) {
    if (!sessionId) return;
    const id = uid();
    const newTurn: Turn = { id, query, response: null, error: null, ts: Date.now() };
    setTurns((t) => [...t, newTurn]);
    setActiveTurnId(id);
    setLoading(true);

    try {
      const r = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query, session_id: sessionId }),
      });
      const data = await r.json();
      if (!r.ok) {
        setTurns((t) =>
          t.map((tt) =>
            tt.id === id ? { ...tt, error: data?.error ?? `HTTP ${r.status}` } : tt,
          ),
        );
      } else {
        const response = data as AskResponse;
        setTurns((t) => t.map((tt) => (tt.id === id ? { ...tt, response } : tt)));
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "network-error";
      setTurns((t) => t.map((tt) => (tt.id === id ? { ...tt, error: message } : tt)));
    } finally {
      setLoading(false);
    }
  }

  function handleNewSession() {
    setTurns([]);
    setSessionId(uid());
    setActiveTurnId(null);
  }

  return (
    <main className="flex h-screen bg-zinc-950">
      <Sidebar
        turns={turns}
        onNewSession={handleNewSession}
        activeTurnId={activeTurnId}
        onSelectTurn={setActiveTurnId}
      />
      <section className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-zinc-800 px-6 py-3">
          <div>
            <h1 className="text-base font-semibold tracking-tight text-zinc-100">
              SCM NL-to-SQL Dashboard
            </h1>
            <p className="text-xs text-zinc-500">
              Domain-Aware Multi-Agent · {sessionId ? `session ${sessionId.slice(0, 8)}` : "initialising…"}
            </p>
          </div>
          <span className="rounded-full border border-emerald-700 bg-emerald-900/30 px-2.5 py-1 text-[10px] font-medium text-emerald-300">
            gpt-4o-mini
          </span>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {turns.length === 0 && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 text-center">
                <h2 className="text-sm font-medium text-zinc-200">
                  Ask any supply-chain question
                </h2>
                <p className="mt-1 text-xs text-zinc-500">
                  Cross-domain composition, multi-turn dialogue, ambiguity-aware refusal — all in one chat.
                  Try one of the sample queries below.
                </p>
              </div>
            )}
            {turns.map((turn) => (
              <TurnView key={turn.id} turn={turn} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <ChatInput onSend={handleSend} disabled={loading || !sessionId} />
      </section>
    </main>
  );
}
