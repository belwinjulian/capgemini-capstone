# Cross-Document Patient Safety Intelligence Assistant

A GraphRAG-based generative AI assistant for healthcare safety teams. Users ask
natural-language questions in plain English and receive source-grounded,
relationship-aware answers synthesized across a corpus of ~100 synthetic
patient safety documents.

Built as a 3-day Capgemini GenAI capstone project, deployed end-to-end on
Google Cloud.

---

## What makes this different from plain RAG

**Plain RAG** — "embed the question, fetch top-k similar chunks, feed them to
an LLM" — works well when the answer lives in a single chunk. It falls over on
**cross-document pattern questions** like *"which medications recur across
adverse event reports?"* The answer isn't in any one chunk; it's a corpus-wide
aggregation spread across dozens of documents.

**GraphRAG** layers an explicit knowledge graph over the same corpus. Entities
(medications, departments, incident types, root causes, staff roles, protocols)
become nodes; relationships (`administered_in`, `caused_by`, `occurred_in`,
etc.) become edges. Every node tracks which documents it appeared in; every
edge carries a `weight` equal to the number of documents corroborating that
relationship.

At query time the system runs **two retrievals in parallel**:

1. **Semantic retrieval** — vector search for the top-5 most similar chunks.
2. **Structural retrieval** — identify which graph nodes appear in those
   chunks (seed entities), then walk 2 hops outward to surface related
   entities and relationships across the whole corpus.

Both are passed to Gemini 2.5 Pro as context. The result: answers that cite
specific source documents *and* surface cross-document patterns with explicit
counts ("this pattern appears in 12 documents: [AER-003], [AER-012], ...").

---

## The 3 demo questions the system answers

1. **"Which medications appear most frequently across adverse event reports?"**
   — requires aggregation across documents. Graph answers it via
   `medication`-type nodes ranked by `len(doc_ids)`.
2. **"What root causes recur across multiple RCA documents?"** — same pattern,
   filtered to `root_cause` type.
3. **"Which departments are most central to sentinel event clusters?"** —
   requires a structural metric. Graph answers it via
   `centrality_by_type(g, "department")` — degree centrality as a proxy for
   "how many distinct things touch this department."

Plus two behavioral tests:

- **Refusal** — *"What is the total financial cost of these adverse events?"*
  The corpus contains no cost data; the model must decline rather than
  hallucinate.
- **Drill-down** — *"Tell me more about the vancomycin incidents."* The UI
  re-populates the force-directed graph around the new seed entity live,
  visually proving the graph is doing real work.

---

## Architecture

```
USER  →  Next.js UI (Cloud Run)  →  FastAPI (Cloud Run)
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                                                     │
              ▼                                                     ▼
    ┌───────────────────┐                           ┌────────────────────────┐
    │  Vector Search    │                           │   Graph Traversal      │
    │  (Vertex AI)      │                           │   (NetworkX in-memory) │
    │  top-5 chunks     │                           │   2-hop neighbors      │
    └───────────────────┘                           └────────────────────────┘
              │                                                     │
              └──────────────────────────┬──────────────────────────┘
                                         │
                                         ▼
                          ┌────────────────────────────┐
                          │     Combined Context       │
                          │   (chunks + subgraph)      │
                          └────────────────────────────┘
                                         │
                                         ▼
                          ┌────────────────────────────┐
                          │      Gemini 2.5 Pro        │
                          │  (streaming, temp=0.2,     │
                          │   with [doc_id] citations) │
                          └────────────────────────────┘
                                         │
                                         ▼
                          Server-Sent Events to the UI
                          (meta → token × N → done)
```

---

## Tech stack

### Backend
- **Python 3.11+**, managed with `uv`
- **FastAPI** — async API layer with native streaming support
- **Pydantic v2** — data validation on Document / Entity / Relationship schemas
- **NetworkX `MultiDiGraph`** — in-memory knowledge graph (directed, allows
  multiple edges between the same pair of nodes for different relation types)
- **google-genai SDK on Vertex AI**:
  - `text-embedding-004` (768-dim) — question and chunk embeddings
  - `gemini-2.5-flash` — entity/relationship extraction during ingestion
  - `gemini-2.5-pro` — final answer generation (streaming)
- **Vertex AI Vector Search** — brute-force index with `DOT_PRODUCT_DISTANCE`
  (exact search is fine at 100 docs; we'd switch to tree-AH at scale)
- **tenacity** — exponential-backoff retries on Vertex AI API calls

### Frontend
- **Next.js 14** with App Router, TypeScript
- **Tailwind CSS** + **shadcn/ui** — component library, clinical aesthetic
- **Geist font** (Sans for body, Mono for citations)
- **d3-force** — force-directed knowledge-graph visualization (nodes push apart
  by repulsion, pull together along edges)
- **SSE parsing** — ingests `meta`, `token`, `done` events from the backend

### Cloud Platform
- **Google Cloud Run** — both services, `us-central1`, min-instances=1 on each
  (Vector Search client takes ~10–15s to warm up on cold start; a warm
  instance eliminates this from the demo path)
- **Artifact Registry** — Docker images (`capstone-images/backend:v1`,
  `capstone-images/frontend:v1`)
- **Cloud Build** — builds images server-side via `cloudbuild.*.yaml` configs
- **Cloud Storage** — raw corpus bucket + Cloud Build source tarballs +
  auto-managed Vector Search index storage
- **IAM** — dedicated runtime service account (`capstone-runtime`) with
  `roles/aiplatform.user`, `roles/storage.objectViewer`,
  `roles/secretmanager.secretAccessor`

---

## Repository layout

```
.
├── README.md                       # You are here
├── CLAUDE.md                       # Project spec, prompts, UI principles
├── DEPLOY.md                       # Windows/PowerShell deployment runbook
├── cloudbuild.backend.yaml         # Cloud Build config for the backend image
├── cloudbuild.frontend.yaml        # Cloud Build config for the frontend image
│
├── backend/
│   ├── Dockerfile                  # Python slim + uv + COPY data/
│   ├── pyproject.toml              # uv-managed Python dependencies
│   ├── scripts/                    # One-shot ingestion pipeline
│   │   ├── 01_generate.py          #   Generate 100 synthetic docs via Gemini
│   │   ├── 02_upload.py            #   Upload raw docs to GCS
│   │   ├── 03_extract.py           #   Entity/relationship extraction (Flash)
│   │   ├── 04_build_graph.py       #   Build + pickle the NetworkX graph
│   │   ├── 05_embed.py             #   Chunk, embed, index in Vector Search
│   │   ├── 05b_index_only.py       #   Re-run just the indexing step
│   │   └── 06_teardown.py          #   Undeploy + delete Vector Search
│   └── app/
│       ├── main.py                 # FastAPI entry, CORS, /health
│       ├── config.py               # pydantic-settings (env vars)
│       ├── models.py               # Document, Entity, Relationship schemas
│       ├── api/chat.py             # /api/chat streaming endpoint
│       ├── retrieval/
│       │   ├── embeddings.py       # text-embedding-004 wrapper
│       │   ├── vector_search.py    # Vertex Vector Search client + lifecycle
│       │   └── graphrag.py         # Hybrid retrieval (vector + graph 2-hop)
│       ├── graph/
│       │   ├── builder.py          # NetworkX MultiDiGraph construction
│       │   └── traversal.py        # two_hop_context, centrality_by_type
│       └── ingestion/
│           └── extract.py          # Flash extraction, normalization, aggregation
│
├── frontend/
│   ├── Dockerfile                  # Multi-stage Node/pnpm → Next.js standalone
│   ├── package.json
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                # Main chat page
│   │   └── api/chat/route.ts       # Thin proxy to backend SSE endpoint
│   └── components/chat/
│       ├── ChatInterface.tsx       # Top-level state + SSE consumer
│       ├── Message.tsx             # Markdown rendering + citation chips
│       ├── Citations.tsx           # Hover popovers with source snippets
│       └── GraphPreview.tsx        # d3-force entity/edge visualization
│
├── data/                           # Baked into the backend container image
│   ├── graph.pkl                   # Pickled NetworkX MultiDiGraph
│   ├── chunks.json                 # All chunk metadata (id, doc, text, index)
│   ├── entities.json               # Aggregated entities
│   ├── relationships.json          # Aggregated relationships
│   └── vector_search_ids.json      # Index + endpoint resource names
│
└── corpus/                         # Raw generated docs (not in image)
```

---

## Data contracts

```python
class Document(BaseModel):
    doc_id: str              # e.g., "AER-001"
    doc_type: Literal["adverse_event", "rca", "protocol", "formulary"]
    title: str
    content: str
    metadata: dict
    gcs_uri: str

class Entity(BaseModel):
    name: str                # normalized: lowercase, underscores, no articles
    type: Literal["medication", "department", "incident_type",
                  "staff_role", "root_cause", "protocol"]
    doc_ids: list[str]       # every doc this entity appeared in

class Relationship(BaseModel):
    source: str              # entity name
    target: str              # entity name
    relation: Literal["administered_in", "occurred_in", "performed_by",
                      "caused_by", "documented_in", "violates"]
    doc_ids: list[str]       # documents corroborating this relationship
    weight: int              # len(doc_ids) — used by retriever ranking

class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    entities_used: list[str]
```

---

## The ingestion pipeline (run once)

Each step is a standalone script under `backend/scripts/`; together they
produce the files in `data/` that the backend image ships with.

| # | Script | What it does |
|---|---|---|
| 1 | `01_generate.py` | Prompts Gemini to produce 100 synthetic healthcare documents across four types. Written to `corpus/`. |
| 2 | `02_upload.py` | Uploads `corpus/*.txt` to `gs://capgemini-capstone-494100-corpus`. |
| 3 | `03_extract.py` | For each doc, calls Gemini 2.5 Flash with `response_mime_type="application/json"` and `temperature=0.0` to extract a list of entities and relationships. Parallelized 3-way with a `ThreadPoolExecutor` and tenacity-backed retries. Results written to `data/entities.json` and `data/relationships.json` after a global aggregation step that normalizes names, deduplicates by (type, name) / (source, relation, target), and computes `doc_ids` and `weight`. |
| 4 | `04_build_graph.py` | Constructs a `nx.MultiDiGraph` from the aggregated entities + relationships and pickles it to `data/graph.pkl`. Also prints degree-centrality top-5 per entity type as a sanity check. |
| 5 | `05_embed.py` | Chunks each doc (~500 tokens), embeds each chunk with `text-embedding-004`, uploads the JSONL to GCS, creates a brute-force Matching Engine index, creates a public endpoint, deploys the index to the endpoint. Writes the resource names to `data/vector_search_ids.json`. |

After the ingestion pipeline runs once, **everything** the backend needs at
query time is either (a) a pickled file baked into the Docker image or (b) a
managed Vertex AI service call. There's no runtime database and no network
dependency for graph traversal.

---

## The query pipeline (every request)

```
POST /api/chat  { "question": "Which medications appear most frequently..." }
```

1. **`GraphRAGRetriever.retrieve()`** (`backend/app/retrieval/graphrag.py`)
   - `embed_query()` — 768-dim vector via `text-embedding-004`.
   - `VectorSearchClient.query()` — `find_neighbors()` returns top-5 chunk IDs
     with distances. We join against `chunks.json` (in memory) to get the raw
     text.
   - `_seed_entities_from_chunks()` — for each graph node, check whether its
     normalized name appears in the concatenated text of the retrieved chunks.
     Candidates are ranked by graph degree (well-connected nodes win) and we
     take the top 8 as seeds.
   - `two_hop_context()` — BFS from seeds out to 2 hops. Per-hop fan-out is
     capped at 25 nodes (sorted by degree) to keep the LLM context focused
     instead of flooded.
2. **`format_for_prompt()`** — renders the retrieved chunks and the resulting
   subgraph as two structured strings.
3. **Gemini 2.5 Pro streaming** — `generate_content_stream()` with
   `temperature=0.2` and `ANSWER_PROMPT` (see `backend/app/api/chat.py`).
4. **SSE response** — three event types in order:
   - `meta` — emitted once, before any tokens, containing `citations`,
     `entities_used`, and the subgraph `{nodes, edges}`. The UI uses this to
     populate the right-hand evidence panel *before* the answer text starts
     appearing — which is exactly why the GraphRAG nature of the system is
     visually obvious during the demo.
   - `token` — emitted many times, one per Gemini streaming chunk.
   - `done` — emitted once at the end.

---

## Frontend behavior

- **Proxy route** (`frontend/app/api/chat/route.ts`) — the browser only talks
  to the frontend origin; the frontend proxies SSE to the backend. Keeps CORS
  and (future) auth simple.
- **ChatInterface** — parses SSE, populates the evidence panel on `meta`,
  appends tokens to the current message on `token`, re-enables input on `done`.
- **GraphPreview** — renders the returned subgraph with `d3-force`. Nodes are
  colored by entity type; hop-0 nodes (directly matched in retrieved chunks)
  are rendered larger/darker than hop-1/hop-2 neighbors. Converges to a stable
  layout in ~2 seconds of animation.
- **Citations** — inline `[AER-003]` chips; hover reveals a popover with the
  document title and a ~240-char snippet from the retrieved chunk.

---

## Design decisions (and the trade-offs behind them)

**NetworkX instead of Neo4j.** 100 documents produce ~500 nodes and ~2,000
edges — a toy for any real graph DB. NetworkX keeps the whole graph in process
memory (~few MB pickled), zero operational overhead, sub-millisecond traversal.
At 10M+ docs we'd swap to Neo4j / Amazon Neptune; the `two_hop_context()`
function's signature wouldn't change.

**Two different Gemini models.** Extraction runs 100 times, once per document,
and is a structured-JSON task where reasoning quality matters less than
consistency — Flash is ~10× cheaper and fast enough. Answer generation runs
once per user question and directly shapes the UX — Pro's reasoning quality
is worth it.

**`response_mime_type="application/json"` + `temperature=0.0` on extraction.**
Forces strictly valid JSON output and deterministic behavior. Same document
always produces the same extraction — essential for a reproducible graph.

**`temperature=0.2` on answer generation.** Low enough for fidelity to the
provided context, high enough that answers don't sound robotic.

**Brute-force vector index with `DOT_PRODUCT_DISTANCE`.** At 100 docs × maybe
400 chunks, exact search is cheap. Tree-AH or ScaNN would add operational
complexity with no measurable speedup at this scale.

**Data ships inside the backend container image.** `graph.pkl` and
`chunks.json` are baked in at build time. This simplifies the data contract
(no `gsutil cp` on startup, no async loader), eliminates a runtime GCS
dependency, and makes images reproducible. The trade-off — re-ingestion
requires a rebuild + redeploy — is acceptable at 100 docs; at larger scale
you'd read from GCS on startup.

**`--min-instances 1` on both services.** Cold start on the backend is
~10–15s because the Vertex AI Vector Search client handshake is slow. Keeping
one instance warm trades a few cents per hour for a reliable live demo.

**No LangChain.** Direct SDK calls are easier to debug, version-stable, and
faster. The abstraction LangChain adds isn't valuable at this scope.

**No tests.** A 3-day capstone with 4 people. The 3 demo questions ARE the
tests; we ran them against the corpus at every stage.

---

## Local development

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev
```

Requires ADC (`gcloud auth application-default login`) so the backend can
call Vertex AI from your workstation. Set the environment variables listed
below (`.env.example` is a template).

### Environment variables

```
GOOGLE_CLOUD_PROJECT=capgemini-capstone-494100
VERTEX_AI_LOCATION=us-central1
GCS_BUCKET_NAME=capgemini-capstone-494100-corpus
VECTOR_SEARCH_INDEX_ID=…
VECTOR_SEARCH_ENDPOINT_ID=…
BACKEND_URL=…                  # frontend only
```

---

## Deployment

Full runbook in **[DEPLOY.md](./DEPLOY.md)**. Summary:

1. Authenticate + enable APIs + create Artifact Registry repo.
2. Create the `capstone-runtime` service account with the three IAM roles.
3. Build the backend image via `gcloud builds submit --config cloudbuild.backend.yaml .`
4. Deploy `capstone-backend` to Cloud Run with the runtime SA and env vars.
5. Smoke-test the backend against all three demo questions.
6. Build + deploy the frontend (`cloudbuild.frontend.yaml`) with
   `BACKEND_URL` env var pointing at the backend's Cloud Run URL.

**Teardown:** `gcloud run services delete capstone-backend capstone-frontend`
stops compute billing. The Vector Search index + endpoint are the expensive
items (~$3/hr for the endpoint); run `python backend/scripts/06_teardown.py`
to remove them.

---

## Credits

Capgemini GenAI Accelerator capstone — a 4-person, 3-day build.
