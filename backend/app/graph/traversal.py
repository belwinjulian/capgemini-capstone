"""2-hop neighbor lookup for GraphRAG context assembly."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass
class GraphContext:
    """Subgraph context returned for retrieval."""
    seed_entities: list[str]
    neighbors: list[dict]   # [{"name", "type", "hops", "doc_ids"}]
    edges: list[dict]       # [{"source", "target", "relation", "weight", "doc_ids"}]


def two_hop_context(g: nx.MultiDiGraph, seeds: list[str], max_per_hop: int = 25) -> GraphContext:
    """Return entities + edges within 2 undirected hops of any seed entity.

    Seeds not in the graph are silently skipped. Per-hop fan-out is capped to
    keep the LLM context focused on highly-connected nodes.
    """
    present = [s for s in seeds if s in g]
    if not present:
        return GraphContext(seed_entities=[], neighbors=[], edges=[])

    visited: dict[str, int] = {s: 0 for s in present}
    frontier = list(present)
    for hop in (1, 2):
        next_frontier: set[str] = set()
        for node in frontier:
            for nb in nx.all_neighbors(g, node):
                if nb in visited:
                    continue
                next_frontier.add(nb)
        for nb in sorted(next_frontier, key=lambda n: -g.degree(n))[:max_per_hop]:
            visited[nb] = hop
        frontier = list(next_frontier)

    neighbors = [
        {
            "name": n,
            "type": g.nodes[n].get("type", "unknown"),
            "hops": visited[n],
            "doc_ids": g.nodes[n].get("doc_ids", []),
        }
        for n in visited
    ]

    edges: list[dict] = []
    sub = g.subgraph(visited.keys())
    for u, v, data in sub.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "relation": data.get("relation", ""),
            "weight": data.get("weight", 1),
            "doc_ids": data.get("doc_ids", []),
        })

    return GraphContext(seed_entities=present, neighbors=neighbors, edges=edges)


def centrality_by_type(g: nx.MultiDiGraph, entity_type: str, top_n: int = 10) -> list[tuple[str, float]]:
    """Degree-centrality ranking restricted to nodes of a given entity type.

    Useful for queries like 'which departments are most central'.
    """
    sub_nodes = [n for n, d in g.nodes(data=True) if d.get("type") == entity_type]
    if not sub_nodes:
        return []
    degrees = [(n, g.degree(n)) for n in sub_nodes]
    degrees.sort(key=lambda t: -t[1])
    return [(n, float(d)) for n, d in degrees[:top_n]]
