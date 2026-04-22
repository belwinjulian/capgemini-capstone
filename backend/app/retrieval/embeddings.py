"""Vertex AI text-embedding-004 client (via google-genai SDK)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models import Document

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMS = 768
TARGET_CHARS = 800
OVERLAP_CHARS = 120
BATCH_SIZE = 64

_PARA_SPLIT = re.compile(r"\n\s*\n")


@dataclass
class Chunk:
    chunk_id: str    # "<doc_id>#<chunk_index>"
    doc_id: str
    chunk_index: int
    text: str


def chunk_document(doc: Document) -> list[Chunk]:
    """Split a Document into overlapping ~800-char chunks on paragraph boundaries."""
    paragraphs = [p.strip() for p in _PARA_SPLIT.split(doc.content) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= TARGET_CHARS:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
            tail = buf[-OVERLAP_CHARS:] if len(buf) > OVERLAP_CHARS else buf
            buf = f"{tail}\n\n{para}"
        else:
            for i in range(0, len(para), TARGET_CHARS - OVERLAP_CHARS):
                chunks.append(para[i:i + TARGET_CHARS])
            buf = ""
    if buf:
        chunks.append(buf)
    return [Chunk(f"{doc.doc_id}#{i}", doc.doc_id, i, text) for i, text in enumerate(chunks)]


@retry(
    retry=retry_if_exception_type(APIError),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(8),
    reraise=True,
)
def _embed_batch(client: genai.Client, texts: list[str], task_type: str) -> list[list[float]]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIMS),
    )
    return [list(e.values) for e in response.embeddings]


def embed_chunks(
    chunks: Iterable[Chunk], project: str, location: str = "us-central1"
) -> list[tuple[Chunk, list[float]]]:
    client = genai.Client(vertexai=True, project=project, location=location)
    chunks = list(chunks)
    out: list[tuple[Chunk, list[float]]] = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        vecs = _embed_batch(client, [c.text for c in batch], "RETRIEVAL_DOCUMENT")
        out.extend(zip(batch, vecs))
    return out


def embed_query(query: str, project: str, location: str = "us-central1") -> list[float]:
    client = genai.Client(vertexai=True, project=project, location=location)
    return _embed_batch(client, [query], "RETRIEVAL_QUERY")[0]
