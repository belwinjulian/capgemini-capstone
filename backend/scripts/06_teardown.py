"""Run once when done: undeploy + delete the Vector Search endpoint and index.

Stops the hourly billing on the deployed endpoint. Embeddings remain in GCS so
re-running 05_embed.py later only re-creates the index/endpoint, not the embeddings.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.vector_search import teardown

PROJECT = "capgemini-capstone-494100"
LOCATION = "us-central1"
DATA = Path(__file__).resolve().parent.parent.parent / "data"


def main() -> None:
    ids_path = DATA / "vector_search_ids.json"
    if not ids_path.exists():
        print(f"{ids_path} not found - nothing to tear down")
        return
    ids = json.loads(ids_path.read_text())
    print(f"undeploying + deleting endpoint {ids['endpoint_resource_name']}")
    teardown(PROJECT, LOCATION, ids["endpoint_resource_name"], ids["index_resource_name"])
    ids_path.unlink()
    print("done. billing stopped.")


if __name__ == "__main__":
    main()
