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

  const empty = text.length === 0;

  return (
    <div className="max-w-3xl space-y-3">
      <div className="markdown-body text-sm leading-relaxed text-zinc-900">
        {empty ? (
          <AssistantSkeleton />
        ) : (
          <ReactMarkdown>{text}</ReactMarkdown>
        )}
      </div>
      {citations && citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {citations.map((c, i) => (
            <CitationChip key={c.chunk_id} index={i + 1} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function AssistantSkeleton() {
  return (
    <div className="space-y-2 py-1" aria-label="Loading answer">
      <div className="h-3 w-3/5 rounded bg-zinc-200 animate-pulse" />
      <div className="h-3 w-4/5 rounded bg-zinc-200 animate-pulse" />
      <div className="h-3 w-2/3 rounded bg-zinc-200 animate-pulse" />
    </div>
  );
}

function CitationChip({ index, citation }: { index: number; citation: Citation }) {
  return (
    <span className="group relative inline-flex">
      <span
        tabIndex={0}
        className="inline-flex items-center rounded-sm border border-zinc-200 bg-white px-1.5 py-0.5 font-mono text-[11px] text-zinc-600 transition-colors hover:border-accent/50 hover:text-accent focus:border-accent/50 focus:text-accent focus:outline-none"
      >
        [{index}] {citation.doc_id}
      </span>
      <span
        role="tooltip"
        className="pointer-events-none absolute left-0 top-full z-20 mt-2 w-72 origin-top scale-95 rounded-md border border-zinc-200 bg-white p-3 text-left text-xs text-zinc-700 opacity-0 shadow-sm transition duration-150 ease-out group-hover:scale-100 group-hover:opacity-100 group-focus-within:scale-100 group-focus-within:opacity-100"
      >
        <span className="block font-mono text-[10px] uppercase tracking-widest text-zinc-500">
          {citation.doc_id}
        </span>
        <span className="mt-1 block leading-relaxed text-zinc-600">
          {citation.snippet}
        </span>
      </span>
    </span>
  );
}
