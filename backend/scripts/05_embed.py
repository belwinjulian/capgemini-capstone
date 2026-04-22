"""Run once: chunk corpus, embed via text-embedding-004, push to Vertex Vector Search.

Outputs (to data/):
  chunks.json              - chunk metadata for retrieval-time text lookup
  embeddings.jsonl         - one {"id","embedding"} per line (also uploaded to GCS)
  vector_search_ids.json   - resource names + deployed_index_id for the API to use

WARNING: this deploys a Vector Search endpoint that bills hourly. Run
scripts/06_teardown.py to stop the meter when done.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import storage

from app.models import Document
from app.retrieval.embeddings import EMBEDDING_DIMS, chunk_document, embed_chunks
from app.retrieval.vector_search import (
    DEPLOYED_INDEX_ID, create_endpoint, create_index, deploy,
)

PROJECT = "capgemini-capstone-494100"
LOCATION = "us-central1"
BUCKET = "capgemini-capstone-494100-corpus"
GCS_EMBEDDINGS_PREFIX = "embeddings/"

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS = ROOT / "corpus"
DATA = ROOT / "data"


def chunk_and_embed() -> tuple[list[dict], list[dict]]:
    """Returns (chunks_meta, embedding_records). Saves chunks.json + embeddings.jsonl."""
    docs = [Document.model_validate_json(p.read_text()) for p in sorted(CORPUS.glob("*.json"))]
    all_chunks = [c for d in docs for c in chunk_document(d)]
    print(f"chunked {len(docs)} docs into {len(all_chunks)} chunks")

    print(f"embedding {len(all_chunks)} chunks ...")
    t0 = time.time()
    pairs = embed_chunks(all_chunks, project=PROJECT, location=LOCATION)
    print(f"embedded in {time.time() - t0:.1f}s")

    chunks_meta = [
        {"chunk_id": c.chunk_id, "doc_id": c.doc_id, "chunk_index": c.chunk_index, "text": c.text}
        for c, _ in pairs
    ]
    embedding_records = [{"id": c.chunk_id, "embedding": vec} for c, vec in pairs]

    (DATA / "chunks.json").write_text(json.dumps(chunks_meta, indent=2))
    # Vertex AI Vector Search BATCH_UPDATE rejects `.jsonl`; it requires
    # `.json`, `.csv`, or `.avro` filenames even when the payload is JSONL.
    jsonl_path = DATA / "embeddings.json"
    with jsonl_path.open("w") as f:
        for rec in embedding_records:
            f.write(json.dumps(rec) + "\n")
    print(f"wrote {jsonl_path}")

    return chunks_meta, embedding_records


def upload_embeddings_to_gcs() -> str:
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(f"{GCS_EMBEDDINGS_PREFIX}embeddings.json")
    blob.upload_from_filename(str(DATA / "embeddings.json"))
    uri = f"gs://{BUCKET}/{GCS_EMBEDDINGS_PREFIX}"
    print(f"uploaded embeddings to {uri}")
    return uri


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    chunk_and_embed()
    contents_delta_uri = upload_embeddings_to_gcs()

    print("creating Vector Search index (this takes ~5-10 min) ...")
    t0 = time.time()
    index = create_index(PROJECT, LOCATION, contents_delta_uri, dimensions=EMBEDDING_DIMS)
    print(f"index created in {time.time() - t0:.1f}s -> {index.resource_name}")

    print("creating endpoint ...")
    endpoint = create_endpoint(PROJECT, LOCATION)
    print(f"endpoint created -> {endpoint.resource_name}")

    print("deploying index to endpoint (~20-30 min, hourly billing starts now) ...")
    t0 = time.time()
    deploy(endpoint, index)
    print(f"deployed in {time.time() - t0:.1f}s")

    ids = {
        "index_resource_name": index.resource_name,
        "endpoint_resource_name": endpoint.resource_name,
        "deployed_index_id": DEPLOYED_INDEX_ID,
    }
    (DATA / "vector_search_ids.json").write_text(json.dumps(ids, indent=2))
    print(f"saved {DATA / 'vector_search_ids.json'}")


if __name__ == "__main__":
    main()
