export type GraphNode = {
  name: string;
  type: string;
  hops: number;
  doc_ids?: string[];
};

export type GraphEdge = {
  source: string;
  target: string;
  relation: string;
  weight: number;
};

export function GraphPreview({
  nodes,
  edges,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
}) {
  const seeds = nodes.filter((n) => n.hops === 0);
  const oneHop = nodes.filter((n) => n.hops === 1).slice(0, 10);

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium text-zinc-700">Entities traversed</h3>
      <div className="space-y-1.5">
        <div className="flex flex-wrap gap-1.5">
          {seeds.map((n) => (
            <span
              key={n.name}
              title={`${n.type} · ${n.doc_ids?.length ?? 0} docs`}
              className="rounded-full border border-accent/40 bg-accent/10 px-2 py-0.5 font-mono text-[11px] text-accent"
            >
              {n.name}
            </span>
          ))}
        </div>
        {oneHop.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {oneHop.map((n) => (
              <span
                key={n.name}
                title={`${n.type} · 1-hop`}
                className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 font-mono text-[11px] text-zinc-500"
              >
                {n.name}
              </span>
            ))}
          </div>
        )}
      </div>
      <p className="text-[10px] text-zinc-400">
        {nodes.length} entities · {edges.length} relationships
      </p>
    </div>
  );
}
