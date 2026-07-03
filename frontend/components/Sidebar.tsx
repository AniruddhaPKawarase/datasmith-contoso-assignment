"use client";

import type { Turn } from "@/lib/types";
import { MessageSquare, Sparkles } from "lucide-react";

type Props = {
  turns: Turn[];
  onNewSession: () => void;
  activeTurnId: string | null;
  onSelectTurn: (id: string) => void;
};

export function Sidebar({ turns, onNewSession, activeTurnId, onSelectTurn }: Props) {
  return (
    <aside className="hidden h-full w-72 flex-col border-r border-zinc-800 bg-zinc-950 md:flex">
      <div className="border-b border-zinc-800 p-4">
        <button
          onClick={onNewSession}
          className="flex w-full items-center justify-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm font-medium text-zinc-100 transition hover:bg-zinc-800"
        >
          <Sparkles size={16} /> New session
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <p className="px-4 pt-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
          History
        </p>
        {turns.length === 0 && (
          <p className="px-4 py-3 text-xs text-zinc-600">No turns yet.</p>
        )}
        <ul className="space-y-1 p-2">
          {turns.map((turn) => (
            <li key={turn.id}>
              <button
                onClick={() => onSelectTurn(turn.id)}
                className={`flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-xs transition ${
                  activeTurnId === turn.id
                    ? "bg-zinc-800 text-zinc-100"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
                }`}
              >
                <MessageSquare size={14} className="mt-0.5 shrink-0" />
                <span className="line-clamp-2">{turn.query}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
      <footer className="border-t border-zinc-800 p-3 text-[10px] text-zinc-600">
        <p>SCM NL-to-SQL</p>
        <p>gpt-4o-mini · v0.9</p>
      </footer>
    </aside>
  );
}
