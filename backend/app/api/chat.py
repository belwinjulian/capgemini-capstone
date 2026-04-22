"""/api/chat streaming endpoint."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import get_settings
from app.retrieval.graphrag import GraphRAGRetriever, format_for_prompt

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA = ROOT / "data"

ANSWER_MODEL = "gemini-2.5-pro"

ANSWER_PROMPT = """You are a patient safety intelligence assistant. Answer the user's question using
ONLY the provided context. Every factual claim must cite a source document using
[doc_id] notation.

If the context does not contain enough information to answer, say so - do not hallucinate.

When the context shows patterns across multiple documents, explicitly surface them:
"This pattern appears in N documents: [AER-003], [AER-012]..."

## Retrieved text chunks:
{chunks}

## Related entities from knowledge graph:
{graph_context}

## User question:
{question}
"""

router = APIRouter()
_retriever: GraphRAGRetriever | None = None
_genai_client: genai.Client | None = None


def _get_retriever() -> GraphRAGRetriever:
    global _retriever
    if _retriever is None:
        s = get_settings()
        ids = json.loads((DATA / "vector_search_ids.json").read_text())
        _retriever = GraphRAGRetriever(
            project=s.google_cloud_project,
            location=s.vertex_ai_location,
            endpoint_resource_name=ids["endpoint_resource_name"],
            deployed_index_id=ids["deployed_index_id"],
            graph_path=DATA / "graph.pkl",
            chunks_path=DATA / "chunks.json",
        )
    return _retriever


def _get_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        s = get_settings()
        _genai_client = genai.Client(vertexai=True, project=s.google_cloud_project,
                                     location=s.vertex_ai_location)
    return _genai_client


class ChatRequest(BaseModel):
    question: str
    k: int = 5


@router.post("/api/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    retriever = _get_retriever()
    result = retriever.retrieve(req.question, k=req.k)
    chunks_str, graph_str = format_for_prompt(result)
    prompt = ANSWER_PROMPT.format(
        chunks=chunks_str, graph_context=graph_str, question=req.question
    )
    citations = [
        {"doc_id": c.doc_id, "chunk_id": c.chunk_id, "snippet": c.text[:240]}
        for c in result.chunks
    ]
    entities_used = [n["name"] for n in result.graph.neighbors if n["hops"] == 0]

    client = _get_client()

    def event_stream():
        yield f"data: {json.dumps({'type': 'meta', 'citations': citations, 'entities': entities_used, 'graph': {'nodes': result.graph.neighbors, 'edges': result.graph.edges}})}\n\n"
        stream = client.models.generate_content_stream(
            model=ANSWER_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        for chunk in stream:
            if chunk.text:
                yield f"data: {json.dumps({'type': 'token', 'text': chunk.text})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
