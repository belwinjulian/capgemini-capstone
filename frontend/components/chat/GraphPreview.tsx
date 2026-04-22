"use client";

import { useEffect, useMemo, useState } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
} from "d3-force";

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

type SimNode = GraphNode & { x: number; y: number };
type SimLink = {
  source: SimNode;
  target: SimNode;
  relation: string;
  weight: number;
};

const WIDTH = 330;
const HEIGHT = 320;
const MAX_ONE_HOP = 12;
const MAX_EDGES = 28;

export function GraphPreview({
  nodes,
  edges,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
}) {
  const { trimmedNodes, trimmedEdges, labelSet } = useMemo(() => {
    const seeds = nodes.filter((n) => n.hops === 0);
    const seedNames = new Set(seeds.map((s) => s.name));
    const oneHop = nodes.filter((n) => n.hops === 1);

    // Rank 1-hop nodes by edges connecting them to seeds (more-connected = more informative).
    const seedDegree = new Map<string, number>();
    for (const e of edges) {
      const sHit = seedNames.has(e.source);
      const tHit = seedNames.has(e.target);
      if (sHit && !tHit) seedDegree.set(e.target, (seedDegree.get(e.target) ?? 0) + e.weight);
      if (tHit && !sHit) seedDegree.set(e.source, (seedDegree.get(e.source) ?? 0) + e.weight);
    }
    const rankedOneHop = [...oneHop].sort(
      (a, b) => (seedDegree.get(b.name) ?? 0) - (seedDegree.get(a.name) ?? 0),
    );
    const keptOneHop = rankedOneHop.slice(0, MAX_ONE_HOP);

    const keep = new Set([...seeds, ...keptOneHop].map((n) => n.name));
    const trimmedNodes = [...seeds, ...keptOneHop];

    // Prefer seed-touching edges, then by weight.
    const candidateEdges = edges.filter(
      (e) => keep.has(e.source) && keep.has(e.target),
    );
    candidateEdges.sort((a, b) => {
      const aSeed = seedNames.has(a.source) || seedNames.has(a.target) ? 1 : 0;
      const bSeed = seedNames.has(b.source) || seedNames.has(b.target) ? 1 : 0;
      if (aSeed !== bSeed) return bSeed - aSeed;
      return b.weight - a.weight;
    });
    const trimmedEdges = candidateEdges.slice(0, MAX_EDGES);

    // Label: seeds always, plus top 5 most-connected 1-hop.
    const labelSet = new Set<string>(seeds.map((s) => s.name));
    keptOneHop.slice(0, 5).forEach((n) => labelSet.add(n.name));

    return { trimmedNodes, trimmedEdges, labelSet };
  }, [nodes, edges]);

  const [layout, setLayout] = useState<{
    nodes: SimNode[];
    links: SimLink[];
  } | null>(null);

  useEffect(() => {
    if (trimmedNodes.length === 0) {
      setLayout(null);
      return;
    }
    const simNodes: SimNode[] = trimmedNodes.map((n) => ({
      ...n,
      x: WIDTH / 2 + (Math.random() - 0.5) * 60,
      y: HEIGHT / 2 + (Math.random() - 0.5) * 60,
    }));
    const byName = new Map(simNodes.map((n) => [n.name, n]));
    const simLinks = trimmedEdges
      .map((e) => {
        const s = byName.get(e.source);
        const t = byName.get(e.target);
        return s && t
          ? { source: s, target: t, relation: e.relation, weight: e.weight }
          : null;
      })
      .filter((x): x is SimLink => x !== null);

    const sim = forceSimulation(simNodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.name)
          .distance(70)
          .strength(0.5),
      )
      .force("charge", forceManyBody().strength(-340))
      .force("center", forceCenter(WIDTH / 2, HEIGHT / 2))
      .force(
        "collide",
        forceCollide<SimNode>().radius((d) => (d.hops === 0 ? 26 : 16)),
      )
      .stop();

    for (let i = 0; i < 400; i++) sim.tick();

    const pad = 14;
    for (const n of simNodes) {
      n.x = Math.max(pad, Math.min(WIDTH - pad, n.x));
      n.y = Math.max(pad, Math.min(HEIGHT - pad, n.y));
    }

    setLayout({ nodes: simNodes, links: simLinks });
  }, [trimmedNodes, trimmedEdges]);

  if (!layout || layout.nodes.length === 0) {
    return null;
  }

  const seedCount = trimmedNodes.filter((n) => n.hops === 0).length;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-medium text-zinc-700">Graph traversal</h3>
      <div className="rounded-md border border-zinc-200 bg-white">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="w-full h-auto"
          role="img"
          aria-label="Knowledge graph nodes traversed to produce the answer"
        >
          <g stroke="#e4e4e7" strokeWidth={1}>
            {layout.links.map((l, i) => (
              <line
                key={i}
                x1={l.source.x}
                y1={l.source.y}
                x2={l.target.x}
                y2={l.target.y}
              >
                <title>{`${l.source.name} → ${l.target.name}  (${l.relation})`}</title>
              </line>
            ))}
          </g>
          <g>
            {layout.nodes.map((n) => {
              const isSeed = n.hops === 0;
              const r = isSeed ? 6 : 3.5;
              const fill = isSeed ? "#0F766E" : "#ffffff";
              const stroke = isSeed ? "#0F766E" : "#a1a1aa";
              const showLabel = labelSet.has(n.name);
              const anchorEnd = n.x > WIDTH / 2;
              return (
                <g key={n.name} transform={`translate(${n.x},${n.y})`}>
                  <circle r={r} fill={fill} stroke={stroke} strokeWidth={1.25}>
                    <title>{`${n.name} · ${n.type}${
                      n.doc_ids?.length ? ` · ${n.doc_ids.length} docs` : ""
                    }`}</title>
                  </circle>
                  {showLabel && (
                    <text
                      x={anchorEnd ? -(r + 3) : r + 3}
                      y={3}
                      textAnchor={anchorEnd ? "end" : "start"}
                      fontSize={isSeed ? 9.5 : 8.5}
                      fontFamily="var(--font-geist-mono), ui-monospace, monospace"
                      fill={isSeed ? "#0F766E" : "#52525b"}
                      style={{ pointerEvents: "none" }}
                    >
                      {n.name}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </div>
      <p className="text-[10px] text-zinc-400 font-mono">
        {seedCount} seed · {trimmedNodes.length - seedCount} related ·{" "}
        {layout.links.length} edges
      </p>
    </div>
  );
}
