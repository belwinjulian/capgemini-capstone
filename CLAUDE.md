# Cross-Document Patient Safety Intelligence Assistant

## Project Overview

A **GraphRAG-based generative AI assistant** for healthcare safety teams. Users ask natural-language questions, and the system returns source-grounded, relationship-aware answers synthesized across a corpus of ~100 patient safety documents.

This is a 3-day capstone for Capgemini's GenAI series. 4-person team. **We are in GSD mode — end-to-end working demo beats perfect code every time.**

---

## The Core Idea (Read This First)

**Plain RAG** returns isolated text chunks. It can't answer "which medications recur across ICU incidents?" because that requires synthesizing across many documents AND understanding entity relationships.

**GraphRAG** combines:
1. **Vector search** — finds semantically similar text chunks
2. **Knowledge graph traversal** — finds related entities through explicit relationships

The LLM gets both as context, producing answers that surface cross-document patterns.

---

## Success Criteria (What Must Work for the Demo)

The system must correctly answer these 3 questions against our synthetic corpus:

1. **"Which medications appear most frequently across adverse event reports?"**
2. **"What root causes recur across multiple RCA documents?"**
3. **"Which departments are most central to sentinel event clusters?"**

Every answer must cite source documents. UI must look professional. That's the whole bar.

---

## Tech Stack (Non-Negotiable)

### Backend
- **Python 3.11+**
- **FastAPI** — async API layer (not Flask — faster, auto-docs, streaming support)
- **Google Cloud Storage** — raw document storage
- **Vertex AI** — `text-embedding-004` for embeddings, **Gemini 2.0 Flash** for entity extraction (cheap + fast), **Gemini 1.5 Pro** for final answer generation
- **Vertex AI Vector Search** — semantic retrieval
- **NetworkX** — in-memory knowledge graph (NOT Neo4j — overkill for 100 docs)
- **Secret Manager** — all credentials
- **Pydantic v2** — data validation on all entity/relationship objects

### Frontend
- **Next.js 14** with App Router + TypeScript
- **shadcn/ui** — component library (copy-paste, looks professional by default)
- **Tailwind CSS** — styling
- **Lucide React** — icons
- **Geist font** (Vercel's font, not Inter)
- **Vercel AI SDK** (`ai` package) — streaming chat UI
- **react-markdown** — render LLM output with formatting

### Deployment
- **Cloud Run** — backend API
- **Vercel** — frontend (easier than Cloud Run for Next.js; free tier fine for demo)

### Dev Tools
- **uv** for Python dependency management (faster than pip/poetry)
- **pnpm** for frontend
- **ruff** for Python linting
- **Git + GitHub** (private repo)

---

## Architecture

```
USER  →  Next.js UI (Vercel)  →  FastAPI (Cloud Run)
                                      |
              +-----------------------+----------------------+
              |                                              |
              v                                              v
     [ Vector Search ]                           [ Graph Traversal ]
     (Vertex AI)                                 (NetworkX in-memory)
     top-5 chunks                                2-hop neighbors
              |                                              |
              +-----------------------+----------------------+
                                      |
                                      v
                          [ Combined Context ]
                          (chunks + entities)
                                      |
                                      v
                          [ Gemini 1.5 Pro ]
                          (generate answer
                          with citations)
                                      |
                                      v
                              Stream to UI
```

---

## Repository Structure

```
/
├── CLAUDE.md                    # This file
├── README.md                    # Setup instructions
├── .env.example                 # Template for env vars
├── .gitignore
│
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── models.py            # Pydantic schemas
│   │   ├── ingestion/
│   │   │   ├── generate_docs.py # Synthetic doc generation
│   │   │   ├── upload_gcs.py    # Upload to GCS
│   │   │   └── extract.py       # Entity extraction via Gemini
│   │   ├── graph/
│   │   │   ├── builder.py       # NetworkX graph construction
│   │   │   └── traversal.py     # 2-hop neighbor lookup
│   │   ├── retrieval/
│   │   │   ├── embeddings.py    # text-embedding-004 calls
│   │   │   ├── vector_search.py # Vertex Vector Search client
│   │   │   └── graphrag.py      # The hybrid retrieval logic
│   │   └── api/
│   │       └── chat.py          # /api/chat endpoint (streaming)
│   ├── scripts/
│   │   ├── 01_generate.py       # Run once: create synthetic docs
│   │   ├── 02_upload.py         # Run once: upload to GCS
│   │   ├── 03_extract.py        # Run once: extract entities
│   │   ├── 04_build_graph.py    # Run once: build + pickle graph
│   │   └── 05_embed.py          # Run once: embed + index
│   └── Dockerfile
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx             # Main chat page
    │   └── api/
    │       └── chat/route.ts    # Proxies to backend
    ├── components/
    │   ├── chat/
    │   │   ├── ChatInterface.tsx
    │   │   ├── Message.tsx
    │   │   ├── Citations.tsx
    │   │   └── GraphPreview.tsx # Shows entities used
    │   └── ui/                  # shadcn components
    └── lib/
        └── utils.ts
```

---

## Data Contracts (Everyone Codes to These)

### Document
```python
class Document(BaseModel):
    doc_id: str              # e.g., "AER-001"
    doc_type: Literal["adverse_event", "rca", "protocol", "formulary"]
    title: str
    content: str
    metadata: dict
    gcs_uri: str
```

### Extracted Entity
```python
class Entity(BaseModel):
    name: str                # normalized: lowercase, stripped
    type: Literal["medication", "department", "incident_type",
                  "staff_role", "root_cause", "protocol"]
    doc_ids: list[str]       # documents this entity appears in
```

### Relationship
```python
class Relationship(BaseModel):
    source: str              # entity name
    target: str              # entity name
    relation: str            # e.g., "administered_in", "caused_by"
    doc_ids: list[str]       # supporting documents
    weight: int = 1          # frequency across corpus
```

### Chat Response
```python
class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    entities_used: list[str]  # for the "graph preview" UI feature
```

---

## Implementation Order (Strict — Do Not Skip Ahead)

### Day 1 — Spine (end-to-end crappy version)
1. Scaffold repo structure (both backend + frontend)
2. Generate 20 synthetic docs (not 100 yet — just enough to test)
3. Upload to GCS
4. Extract entities on those 20 docs
5. Build graph, pickle it
6. Embed chunks, index in Vector Search
7. Stub retrieval function (can return hardcoded answer)
8. Wire FastAPI endpoint
9. Scaffold Next.js chat UI — can hit backend, display response
10. **Goal by end of Day 1: you can type a question in the UI and get ANY response back from the backend.**

### Day 2 — Make it real
1. Scale up to 100 synthetic docs
2. Re-run extraction + graph build + embedding
3. Implement actual GraphRAG retrieval logic (vector + graph combined)
4. Streaming LLM response via Vercel AI SDK
5. Citations rendering in UI
6. Test against the 3 example questions — iterate prompts until answers are good
7. **Goal by end of Day 2: the 3 example questions return good answers.**

### Day 3 — Polish + deploy
1. Deploy backend to Cloud Run
2. Deploy frontend to Vercel
3. Graph visualization component (show entities/edges used in answer)
4. Clean up UI, professional styling pass
5. Demo script + practice runs
6. Slide deck

---

## UI Design Principles (IMPORTANT — This Is What Separates Us)

**Avoid the vibe-coded look.** No purple gradients, no sparkle emojis in headers, no generic Inter font, no rounded-xl everywhere.

### Aesthetic: Clinical Minimalism
- **Colors:** Near-white background (`#FAFAFA`), dark text (`#0A0A0A`), one accent color — **deep teal** (`#0F766E`). That's it.
- **Typography:** Geist Sans for body, Geist Mono for code/citations. Tight tracking on headers.
- **Spacing:** Generous. Breathing room signals quality.
- **Borders:** Subtle 1px borders (`border-zinc-200`) instead of shadows.
- **Radius:** `rounded-md` max. Never `rounded-full` on buttons.
- **Icons:** Lucide, small, consistent stroke weight.

### Layout
- Two-column: left = chat, right = "evidence panel" showing which entities/documents the current answer used (this is the killer visual — it makes GraphRAG *visible*).
- Sticky header with project name + small "Capgemini" wordmark.
- Messages: user messages right-aligned in muted background, assistant messages full-width with citations inline.
- Citations render as small numbered chips `[1]` `[2]` that expand on hover to show doc title + snippet.

### Components to Use from shadcn/ui
- `Button`, `Input`, `Card`, `ScrollArea`, `Sheet` (for mobile), `Tooltip`, `Badge`, `Separator`, `Skeleton` (loading states)

### The Killer Feature
A small **graph preview** next to each answer showing the 5-10 entities the system traversed to build that answer. Use `react-force-graph-2d` or just SVG with d3-force. This visually proves GraphRAG > plain RAG. Judges will remember this.

---

## Prompts to Use

### For entity extraction (Gemini 2.0 Flash)
```
You are extracting structured knowledge from a healthcare incident document.

Return ONLY valid JSON matching this schema:
{
  "entities": [{"name": str, "type": str}],
  "relationships": [{"source": str, "target": str, "relation": str}]
}

Entity types: medication, department, incident_type, staff_role, root_cause, protocol
Relation types: administered_in, occurred_in, performed_by, caused_by, documented_in, violates

Normalize entity names: lowercase, no articles ("the ICU" -> "icu"), use standard
medical abbreviations where common (ICU, ER, OR).

Document:
{doc_content}
```

### For final answer generation (Gemini 1.5 Pro)
```
You are a patient safety intelligence assistant. Answer the user's question using
ONLY the provided context. Every factual claim must cite a source document using
[doc_id] notation.

If the context does not contain enough information to answer, say so — do not
hallucinate.

When the context shows patterns across multiple documents, explicitly surface them:
"This pattern appears in 5 documents: [AER-003], [AER-012]..."

## Retrieved text chunks:
{chunks}

## Related entities from knowledge graph:
{graph_context}

## User question:
{question}
```

---

## Environment Variables

```
GOOGLE_CLOUD_PROJECT=
GCS_BUCKET_NAME=
VERTEX_AI_LOCATION=us-central1
VECTOR_SEARCH_INDEX_ID=
VECTOR_SEARCH_ENDPOINT_ID=
BACKEND_URL=  # for frontend
```

All pulled from Secret Manager in prod, `.env` locally.

---

## What NOT to Do

- Don't use LangChain. Too much magic, too many versions, too slow to debug. Call APIs directly.
- Don't use Neo4j. Overkill for 100 docs. NetworkX is 10 lines of code.
- Don't build authentication. Demo is public or IP-gated. No login flow.
- Don't write tests. 3 days. The 3 example questions ARE the tests.
- Don't optimize performance. Everything runs offline except the final LLM call.
- Don't refactor. Whatever structure emerges in the first hour is the structure for the whole project.
- Don't use Flask. FastAPI is the same effort and streams responses natively.
- Don't use Material UI or Chakra. shadcn/ui looks 10x better.

---

## When Stuck

Prioritize in this order:
1. Does it work end-to-end? If no → fix that.
2. Does it answer the 3 demo questions? If no → fix the prompts.
3. Does the UI look professional? If no → more whitespace, simpler palette.
4. Everything else is out of scope.