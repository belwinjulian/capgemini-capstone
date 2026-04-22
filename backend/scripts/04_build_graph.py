"""Run once: build NetworkX knowledge graph from extractions and pickle it."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.builder import build_graph, save
from app.graph.traversal import centrality_by_type
from app.models import Entity, Relationship

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def main() -> None:
    entities = [Entity.model_validate(e) for e in json.loads((DATA / "entities.json").read_text())]
    relationships = [Relationship.model_validate(r)
                     for r in json.loads((DATA / "relationships.json").read_text())]

    g = build_graph(entities, relationships)
    print(f"graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")

    out = DATA / "graph.pkl"
    save(g, out)
    print(f"pickled to {out}")

    print("\nDegree centrality by entity type (top 5 each):")
    for t in ("department", "medication", "root_cause", "incident_type"):
        ranked = centrality_by_type(g, t, top_n=5)
        print(f"  {t}:")
        for name, deg in ranked:
            print(f"    {name}: {deg:.0f}")


if __name__ == "__main__":
    main()
