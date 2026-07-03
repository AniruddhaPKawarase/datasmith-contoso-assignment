"use client";

import { useState, type KeyboardEvent } from "react";
import { Send } from "lucide-react";

type Props = {
  onSend: (query: string) => void;
  disabled: boolean;
};

const SAMPLE_QUERIES = [
  "Show monthly revenue for 2009 by region",
  "Who are our top 10 customers by lifetime value?",
  "Show revenue by product category for 2009",
  "Show me a sales funnel: orders → shipped → revenue by territory",
];

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");

  function handleSend() {
    const q = value.trim();
    if (!q || disabled) return;
    onSend(q);
    setValue("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="border-t border-zinc-800 bg-zinc-950 p-4">
      <div className="mx-auto max-w-3xl">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {SAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => setValue(q)}
              disabled={disabled}
              className="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-[11px] text-zinc-400 transition hover:border-zinc-700 hover:text-zinc-200 disabled:opacity-40"
            >
              {q.slice(0, 60)}
              {q.length > 60 ? "…" : ""}
            </button>
          ))}
        </div>
        <div className="flex items-end gap-2 rounded-xl border border-zinc-700 bg-zinc-900 p-2 focus-within:border-zinc-500">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your supply chain… (Enter to send, Shift+Enter for newline)"
            disabled={disabled}
            rows={2}
            className="flex-1 resize-none bg-transparent px-2 py-1 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={disabled || !value.trim()}
            className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 text-white transition hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
