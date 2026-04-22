"""Entity + relationship extraction via Gemini 2.5 Flash (google-genai SDK on Vertex AI)."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable

from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models import Document, Entity, Relationship

VALID_ENTITY_TYPES = {
    "medication", "department", "incident_type", "staff_role", "root_cause", "protocol"
}
VALID_RELATIONS = {
    "administered_in", "occurred_in", "performed_by", "caused_by", "documented_in", "violates"
}

EXTRACTION_PROMPT = """You are extracting structured knowledge from a healthcare incident document.

Return ONLY valid JSON matching this schema:
{{
  "entities": [{{"name": "string", "type": "string"}}],
  "relationships": [{{"source": "string", "target": "string", "relation": "string"}}]
}}

Entity types: medication, department, incident_type, staff_role, root_cause, protocol
Relation types: administered_in, occurred_in, performed_by, caused_by, documented_in, violates

Normalize entity names: lowercase, no articles ("the ICU" -> "icu"), use standard
medical abbreviations where common (ICU, ER, OR).

Document:
{doc_content}
"""

MODEL_NAME = "gemini-2.5-flash"
_NON_ALNUM = re.compile(r"[^a-z0-9_]+")


@dataclass
class DocExtraction:
    doc_id: str
    entities: list[dict]
    relationships: list[dict]


def _normalize(name: str) -> str:
    name = name.strip().lower()
    for article in ("the ", "a ", "an "):
        if name.startswith(article):
            name = name[len(article):]
    name = name.replace(" ", "_").replace("-", "_")
    name = _NON_ALNUM.sub("", name)
    return name


def _is_rate_limit(exc: BaseException) -> bool:
    return isinstance(exc, APIError) and getattr(exc, "code", None) in (429, 503)


@retry(
    retry=retry_if_exception_type(APIError),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(8),
    reraise=True,
)
def _generate_with_retry(client: genai.Client, prompt: str) -> str:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    return response.text


def _extract_one(client: genai.Client, doc: Document) -> DocExtraction:
    prompt = EXTRACTION_PROMPT.format(doc_content=doc.content)
    text = _generate_with_retry(client, prompt)
    data = json.loads(text)
    raw_entities = data.get("entities", [])
    raw_relationships = data.get("relationships", [])
    entities = [
        {"name": _normalize(e["name"]), "type": e["type"]}
        for e in raw_entities
        if e.get("name") and e.get("type") in VALID_ENTITY_TYPES
    ]
    relationships = [
        {
            "source": _normalize(r["source"]),
            "target": _normalize(r["target"]),
            "relation": r["relation"],
        }
        for r in raw_relationships
        if r.get("source") and r.get("target") and r.get("relation") in VALID_RELATIONS
    ]
    return DocExtraction(doc.doc_id, entities, relationships)


def extract_corpus(
    docs: Iterable[Document],
    project: str,
    location: str = "us-central1",
    max_workers: int = 3,
) -> list[DocExtraction]:
    client = genai.Client(vertexai=True, project=project, location=location)
    docs = list(docs)
    results: list[DocExtraction] = []
    errors: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_extract_one, client, doc): doc for doc in docs}
        for fut in as_completed(futures):
            doc = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                errors.append((doc.doc_id, str(exc)))
    if errors:
        print(f"warning: {len(errors)} extraction errors")
        for doc_id, msg in errors[:5]:
            print(f"  {doc_id}: {msg[:200]}")
    return results


def aggregate(extractions: list[DocExtraction]) -> tuple[list[Entity], list[Relationship]]:
    """Merge per-doc extractions into global Entity + Relationship lists.

    Entities are keyed by (type, name) and track every doc_id they appear in.
    Relationships are keyed by (source, relation, target); weight counts docs.
    """
    entity_map: dict[tuple[str, str], set[str]] = {}
    rel_map: dict[tuple[str, str, str], set[str]] = {}
    for ext in extractions:
        for e in ext.entities:
            key = (e["type"], e["name"])
            entity_map.setdefault(key, set()).add(ext.doc_id)
        for r in ext.relationships:
            key = (r["source"], r["relation"], r["target"])
            rel_map.setdefault(key, set()).add(ext.doc_id)
    entities = [
        Entity(name=name, type=etype, doc_ids=sorted(doc_ids))
        for (etype, name), doc_ids in entity_map.items()
    ]
    relationships = [
        Relationship(
            source=src, target=tgt, relation=rel,
            doc_ids=sorted(doc_ids), weight=len(doc_ids),
        )
        for (src, rel, tgt), doc_ids in rel_map.items()
    ]
    return entities, relationships
