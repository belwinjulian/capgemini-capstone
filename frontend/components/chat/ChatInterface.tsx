"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { Message } from "./Message";
import { Citations, type Citation } from "./Citations";
import { GraphPreview, type GraphEdge, type GraphNode } from "./GraphPreview";

type ChatTurn = {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  entities?: string[];
  graph?: { nodes: GraphNode[]; edges: GraphEdge[] };
};

const EXAMPLES = [
  "Which medications appear most frequently across adverse event reports?",
  "What root causes recur across multiple RCA documents?",
  "Which departments are most central to sentinel event clusters?",
];

export function ChatInterface() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function ask(question: string) {
    if (!question.trim() || loading) return;
    setLoading(true);
    setTurns((prev) => [
      ...prev,
      { role: "user", text: question },
      { role: "assistant", text: "" },
    ]);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok || !res.body) throw new Error(`backend ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const ev of events) {
          const line = ev.split("\n").find((l) => l.startsWith("data: "));
          if (!line) continue;
          let data: any;
          try {
            data = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          setTurns((prev) => {
            const next = [...prev];
            const last = { ...next[next.length - 1] };
            if (data.type === "meta") {
              last.citations = data.citations;
              last.entities = data.entities;
              last.graph = data.graph;
            } else if (data.type === "token") {
              last.text += data.text;
            }
            next[next.length - 1] = last;
            return next;
          });
        }
      }
    } catch (err) {
      setTurns((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last && last.role === "assistant") {
          last.text = `⚠︎ ${(err as Error).message}`;
        }
        return next;
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q) return;
    setInput("");
    await ask(q);
  }

  const lastAssistant = [...turns].reverse().find((t) => t.role === "assistant");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] h-[calc(100vh-49px)]">
      <section className="flex flex-col border-r border-zinc-200">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {turns.length === 0 && (
            <div className="max-w-xl text-sm text-zinc-600 space-y-3">
              <p className="font-medium text-zinc-800">
                Ask a patient-safety question.
              </p>
              <ul className="space-y-1.5">
                {EXAMPLES.map((q) => (
                  <li key={q}>
                    <button
                      onClick={() => ask(q)}
                      className="text-left text-zinc-600 hover:text-accent underline decoration-zinc-300 hover:decoration-accent underline-offset-4"
                    >
                      {q}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {turns.map((t, i) => (
            <Message
              key={i}
              role={t.role}
              text={t.text}
              citations={t.citations}
            />
          ))}
        </div>
        <form
          onSubmit={handleSubmit}
          className="border-t border-zinc-200 p-4 flex gap-2 bg-white"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the patient safety assistant…"
            className="flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-md bg-accent px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-40 flex items-center gap-1.5"
          >
            <Send className="h-4 w-4" />
            {loading ? "…" : "Send"}
          </button>
        </form>
      </section>
      <aside className="hidden lg:flex flex-col overflow-y-auto p-5 space-y-5">
        <h2 className="font-mono text-[11px] uppercase tracking-widest text-zinc-500">
          Evidence
        </h2>
        {lastAssistant?.citations?.length ? (
          <Citations citations={lastAssistant.citations} />
        ) : (
          <p className="text-xs text-zinc-400">
            Citations appear here after an answer.
          </p>
        )}
        {lastAssistant?.graph?.nodes?.length ? (
          <GraphPreview
            nodes={lastAssistant.graph.nodes}
            edges={lastAssistant.graph.edges}
          />
        ) : null}
      </aside>
    </div>
  );
}
