"""Hybrid retrieval: vector top-k + graph neighbors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from app.graph.builder import load as load_graph
from app.graph.traversal import GraphContext, two_hop_context
from app.retrieval.embeddings import embed_query
from app.retrieval.vector_search import VectorSearchClient


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    score: float


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    graph: GraphContext


class GraphRAGRetriever:
    def __init__(
        self,
        project: str,
        location: str,
        endpoint_resource_name: str,
        deployed_index_id: str,
        graph_path: Path,
        chunks_path: Path,
    ):
        self.project = project
        self.location = location
        self.vs = VectorSearchClient(project, location, endpoint_resource_name, deployed_index_id)
        self.graph: nx.MultiDiGraph = load_graph(graph_path)
        self.chunks_by_id: dict[str, dict] = {
            c["chunk_id"]: c for c in json.loads(chunks_path.read_text())
        }

    def _seed_entities_from_chunks(self, chunks: list[RetrievedChunk], max_seeds: int = 8) -> list[str]:
        """Pick graph nodes that appear (by name) in any retrieved chunk's text."""
        text_blob = " ".join(c.text.lower() for c in chunks)
        candidates: list[tuple[str, int]] = []
        for node in self.graph.nodes:
            token = node.replace("_", " ")
            if token in text_blob:
                candidates.append((node, self.graph.degree(node)))
        candidates.sort(key=lambda t: -t[1])
        return [n for n, _ in candidates[:max_seeds]]

    def retrieve(self, question: str, k: int = 5) -> RetrievalResult:
        q_vec = embed_query(question, project=self.project, location=self.location)
        hits = self.vs.query(q_vec, k=k)
        chunks: list[RetrievedChunk] = []
        for chunk_id, score in hits:
            meta = self.chunks_by_id.get(chunk_id)
            if not meta:
                continue
            chunks.append(RetrievedChunk(
                chunk_id=chunk_id,
                doc_id=meta["doc_id"],
                chunk_index=meta["chunk_index"],
                text=meta["text"],
                score=score,
            ))
        seeds = self._seed_entities_from_chunks(chunks)
        graph_ctx = two_hop_context(self.graph, seeds)
        return RetrievalResult(chunks=chunks, graph=graph_ctx)


def format_for_prompt(result: RetrievalResult) -> tuple[str, str]:
    """Render chunks + graph context as two strings for the answer prompt."""
    chunk_block = "\n\n".join(
        f"[{c.doc_id}] (chunk {c.chunk_index}, score={c.score:.3f})\n{c.text}"
        for c in result.chunks
    )
    nodes = result.graph.neighbors
    edges = result.graph.edges
    if not nodes:
        graph_block = "(no graph context — no seed entities found)"
    else:
        nodes_str = "\n".join(
            f"- {n['name']} ({n['type']}, hops={n['hops']}, in {len(n['doc_ids'])} docs)"
            for n in sorted(nodes, key=lambda x: (x['hops'], -len(x['doc_ids'])))
        )
        edges_str = "\n".join(
            f"- ({e['source']}) -[{e['relation']}]-> ({e['target']}) "
            f"weight={e['weight']} docs={','.join(e['doc_ids'][:5])}"
            for e in sorted(edges, key=lambda x: -x['weight'])[:30]
        )
        graph_block = f"Entities:\n{nodes_str}\n\nEdges:\n{edges_str}"
    return chunk_block, graph_block
