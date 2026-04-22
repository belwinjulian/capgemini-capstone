"""Run once: extract entities + relationships from corpus/ via Gemini 2.5 Flash."""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.extract import aggregate, extract_corpus
from app.models import Document

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS = ROOT / "corpus"
OUT_DIR = ROOT / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    docs = [Document.model_validate_json(p.read_text()) for p in sorted(CORPUS.glob("*.json"))]
    print(f"extracting from {len(docs)} docs ...")
    t0 = time.time()
    extractions = extract_corpus(docs, project="capgemini-capstone-494100", max_workers=10)
    elapsed = time.time() - t0
    print(f"done in {elapsed:.1f}s ({len(extractions)} succeeded, {len(docs) - len(extractions)} failed)")

    entities, relationships = aggregate(extractions)
    print(f"aggregated: {len(entities)} unique entities, {len(relationships)} unique relationships")

    type_counts = Counter(e.type for e in entities)
    print("entities by type:")
    for t, c in type_counts.most_common():
        print(f"  {t}: {c}")

    (OUT_DIR / "extractions.json").write_text(
        json.dumps([{"doc_id": e.doc_id, "entities": e.entities, "relationships": e.relationships}
                    for e in extractions], indent=2)
    )
    (OUT_DIR / "entities.json").write_text(
        json.dumps([e.model_dump() for e in entities], indent=2)
    )
    (OUT_DIR / "relationships.json").write_text(
        json.dumps([r.model_dump() for r in relationships], indent=2)
    )
    print(f"wrote: {OUT_DIR}/extractions.json, entities.json, relationships.json")


if __name__ == "__main__":
    main()
