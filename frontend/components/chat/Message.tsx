"use client";

import ReactMarkdown from "react-markdown";
import type { Citation } from "./Citations";

export function Message({
  role,
  text,
  citations,
}: {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
}) {
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-xl rounded-md bg-zinc-100 px-4 py-2 text-sm text-zinc-900">
          {text}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-3">
      <div className="text-sm leading-relaxed text-zinc-900 whitespace-pre-wrap">
        <ReactMarkdown>{text || "…"}</ReactMarkdown>
      </div>
      {citations && citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {citations.map((c, i) => (
            <span
              key={c.chunk_id}
              title={`${c.doc_id}: ${c.snippet}`}
              className="inline-flex items-center rounded-sm border border-zinc-200 bg-white px-1.5 py-0.5 font-mono text-[11px] text-zinc-600"
            >
              [{i + 1}] {c.doc_id}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
