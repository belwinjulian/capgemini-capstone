export type Citation = {
  doc_id: string;
  chunk_id: string;
  snippet: string;
};

export function Citations({ citations }: { citations: Citation[] }) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium text-zinc-700">Sources</h3>
      <ol className="space-y-2">
        {citations.map((c, i) => (
          <li
            key={c.chunk_id}
            className="rounded-md border border-zinc-200 bg-white p-3 text-xs"
          >
            <div className="font-mono text-[11px] text-zinc-500">
              [{i + 1}] {c.doc_id}
            </div>
            <p className="mt-1 text-zinc-700 line-clamp-4">{c.snippet}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
