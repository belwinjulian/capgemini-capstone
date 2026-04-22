"""Resume step 5 after chunking/embedding succeeded but index creation failed.

Assumes data/embeddings.jsonl exists AND has been uploaded to
gs://<BUCKET>/embeddings/embeddings.jsonl. Creates the Vector Search index,
endpoint, and deploys it. Writes data/vector_search_ids.json.

Run scripts/06_teardown.py when done to stop hourly billing.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.embeddings import EMBEDDING_DIMS
from app.retrieval.vector_search import (
    DEPLOYED_INDEX_ID, create_endpoint, create_index, deploy,
)

PROJECT = "capgemini-capstone-494100"
LOCATION = "us-central1"
BUCKET = "capgemini-capstone-494100-corpus"
GCS_EMBEDDINGS_PREFIX = "embeddings/"

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def main() -> None:
    contents_delta_uri = f"gs://{BUCKET}/{GCS_EMBEDDINGS_PREFIX}"
    print(f"using existing embeddings at {contents_delta_uri}")

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
