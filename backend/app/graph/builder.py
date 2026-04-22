"""NetworkX knowledge-graph construction from extracted entities."""

from __future__ import annotations

import pickle
from pathlib import Path

import networkx as nx

from app.models import Entity, Relationship


def build_graph(entities: list[Entity], relationships: list[Relationship]) -> nx.MultiDiGraph:
    """Build a MultiDiGraph: nodes are entities, edges are relationships.

    Node attributes: type, doc_ids
    Edge attributes (per multi-edge): relation, doc_ids, weight
    """
    g = nx.MultiDiGraph()
    for e in entities:
        g.add_node(e.name, type=e.type, doc_ids=list(e.doc_ids))
    for r in relationships:
        if r.source not in g or r.target not in g:
            continue
        g.add_edge(
            r.source, r.target,
            key=r.relation,
            relation=r.relation,
            doc_ids=list(r.doc_ids),
            weight=r.weight,
        )
    return g


def save(g: nx.MultiDiGraph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(g, f)


def load(path: Path) -> nx.MultiDiGraph:
    with path.open("rb") as f:
        return pickle.load(f)
