"""Run once: upload local corpus/ to GCS and backfill gcs_uri on each file."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.upload_gcs import upload_corpus

CORPUS = Path(__file__).resolve().parent.parent.parent / "corpus"
BUCKET = os.environ.get("GCS_BUCKET_NAME", "capgemini-capstone-494100-corpus")


def main() -> None:
    docs = upload_corpus(CORPUS, BUCKET)
    print(f"uploaded {len(docs)} docs to gs://{BUCKET}/docs/")
    for doc in docs[:3]:
        print(f"  sample: {doc.gcs_uri}")


if __name__ == "__main__":
    main()
