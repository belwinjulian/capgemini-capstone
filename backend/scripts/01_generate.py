"""Run once: generate the synthetic patient-safety corpus into ./corpus/."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.generate_docs import generate_corpus

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "corpus"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    docs = generate_corpus()
    for doc in docs:
        (OUT_DIR / f"{doc.doc_id}.json").write_text(doc.model_dump_json(indent=2))
    counts = Counter(d.doc_type for d in docs)
    print(f"wrote {len(docs)} docs to {OUT_DIR}")
    for doc_type, n in sorted(counts.items()):
        print(f"  {doc_type}: {n}")


if __name__ == "__main__":
    main()
