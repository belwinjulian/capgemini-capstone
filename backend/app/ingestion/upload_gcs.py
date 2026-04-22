"""Upload generated documents to Google Cloud Storage."""

from __future__ import annotations

import json
from pathlib import Path

from google.cloud import storage

from app.models import Document


def upload_corpus(corpus_dir: Path, bucket_name: str, prefix: str = "docs/") -> list[Document]:
    """Upload every *.json in corpus_dir to gs://<bucket>/<prefix><doc_id>.json.

    Returns the list of Document objects with gcs_uri populated.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    uploaded: list[Document] = []
    for path in sorted(corpus_dir.glob("*.json")):
        doc = Document.model_validate_json(path.read_text())
        blob_name = f"{prefix}{doc.doc_id}.json"
        doc.gcs_uri = f"gs://{bucket_name}/{blob_name}"
        bucket.blob(blob_name).upload_from_string(
            doc.model_dump_json(indent=2), content_type="application/json"
        )
        path.write_text(doc.model_dump_json(indent=2))
        uploaded.append(doc)
    return uploaded
