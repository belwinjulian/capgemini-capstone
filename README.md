# Cross-Document Patient Safety Intelligence Assistant

A GraphRAG-based generative AI assistant for healthcare safety teams. Users ask
natural-language questions and receive source-grounded, relationship-aware
answers synthesized across a corpus of ~100 synthetic patient safety documents.

Capgemini GenAI capstone project.

## Structure

- `backend/` — FastAPI service (Python 3.11+, managed with `uv`)
- `frontend/` — Next.js 14 chat UI (TypeScript, Tailwind, shadcn/ui)

## Setup

1. Copy `.env.example` to `.env` and fill in the GCP values.
2. Backend: `cd backend && uv sync && uv run uvicorn app.main:app --reload`
3. Frontend: `cd frontend && pnpm install && pnpm dev`

See `CLAUDE.md` for architecture, data contracts, and implementation plan.
