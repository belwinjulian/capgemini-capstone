# Deploying to Google Cloud (all-GCP, Cloud Run)

Runbook for deploying the Patient Safety Intelligence assistant to
Cloud Run from a fresh Capgemini laptop. Copy-paste the commands in
order. No AI tooling required.

## Assumptions

- GCP project: `capgemini-capstone-494100` (already has Vertex AI,
  Vector Search, and GCS set up from earlier ingestion).
- Active gcloud identity: `belwin.julian-robert-raj@capgemini.com`.
- Region: `us-central1` throughout.
- Repo ZIP downloaded from GitHub and unzipped somewhere (referred
  to below as `$REPO`).

Data files (`data/chunks.json`, `data/graph.pkl`,
`data/vector_search_ids.json`, etc.) are checked into the repo so
the backend image is fully self-contained.

## 0. One-time tool setup on the Capgemini laptop

Install (once, any order):

- Google Cloud CLI: <https://cloud.google.com/sdk/docs/install>
- Docker Desktop (only needed if you want local smoke tests) or skip
  and let Cloud Build do it.

```bash
gcloud auth login                                   # browser SSO
gcloud auth application-default login               # for local runs
gcloud config set project capgemini-capstone-494100
gcloud config set run/region us-central1
gcloud config set artifacts/location us-central1
```

Enable required APIs (idempotent — safe to rerun):

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com
```

## 1. Optional — local smoke test before deploying

```bash
cd $REPO/backend
cat > .env <<'EOF'
GOOGLE_CLOUD_PROJECT=capgemini-capstone-494100
VERTEX_AI_LOCATION=us-central1
EOF
pip install uv
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
# In another terminal:
cd $REPO/frontend
corepack enable && pnpm install
pnpm dev
# Open http://localhost:3000, click a demo question, confirm it
# streams an answer with citations.
```

If that works, deploy. If it fails with `PERMISSION_DENIED` on
Vertex AI, your corporate identity may not have `aiplatform.user`
on the project — ask an admin.

## 2. Create the Artifact Registry repo

```bash
gcloud artifacts repositories create capstone-images \
  --repository-format=docker \
  --location=us-central1 \
  --description="Capstone Cloud Run images"
```

## 3. Create the runtime service account

```bash
gcloud iam service-accounts create capstone-runtime \
  --display-name="Cloud Run runtime for capstone"

PROJECT=capgemini-capstone-494100
SA=capstone-runtime@${PROJECT}.iam.gserviceaccount.com

for ROLE in \
    roles/aiplatform.user \
    roles/storage.objectViewer \
    roles/secretmanager.secretAccessor
do
  gcloud projects add-iam-policy-binding ${PROJECT} \
    --member="serviceAccount:${SA}" --role="${ROLE}"
done
```

## 4. Build + push the backend image

Run from the repo root. The backend Dockerfile expects to see both
`backend/` and `data/` in its build context, so build context = repo
root.

```bash
cd $REPO

gcloud builds submit \
  --tag us-central1-docker.pkg.dev/capgemini-capstone-494100/capstone-images/backend:v1 \
  --file backend/Dockerfile \
  .
```

First build takes ~5 min (Playwright-free, just Python deps).

## 5. Deploy the backend to Cloud Run

```bash
gcloud run deploy capstone-backend \
  --image us-central1-docker.pkg.dev/capgemini-capstone-494100/capstone-images/backend:v1 \
  --service-account capstone-runtime@capgemini-capstone-494100.iam.gserviceaccount.com \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 20 \
  --min-instances 1 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=capgemini-capstone-494100,VERTEX_AI_LOCATION=us-central1"
```

`--min-instances 1` keeps one warm — Vertex AI Vector Search clients
take ~15s to initialize on cold start, which is bad for a live demo.

Capture the backend URL:

```bash
BACKEND_URL=$(gcloud run services describe capstone-backend \
  --region us-central1 --format='value(status.url)')
echo "$BACKEND_URL"

# Smoke test
curl -sS -X POST "$BACKEND_URL/api/chat" \
  -H 'content-type: application/json' \
  -d '{"question":"Which medications appear most frequently across adverse event reports?"}' \
  --no-buffer | head -c 1200
```

You should see a stream of `data: {...}` SSE events. If you see a
401/403, re-check the service account role bindings.

## 6. Build + push the frontend image

```bash
cd $REPO

gcloud builds submit \
  --tag us-central1-docker.pkg.dev/capgemini-capstone-494100/capstone-images/frontend:v1 \
  --file frontend/Dockerfile \
  .
```

## 7. Deploy the frontend to Cloud Run

```bash
gcloud run deploy capstone-frontend \
  --image us-central1-docker.pkg.dev/capgemini-capstone-494100/capstone-images/frontend:v1 \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --min-instances 1 \
  --set-env-vars "BACKEND_URL=${BACKEND_URL}"
```

Capture the frontend URL and open it in a browser:

```bash
FRONTEND_URL=$(gcloud run services describe capstone-frontend \
  --region us-central1 --format='value(status.url)')
echo "$FRONTEND_URL"
open "$FRONTEND_URL"      # macOS
```

## 8. Demo checklist

Before presenting, click each of the three demo questions once to
warm instances:

1. "Which medications appear most frequently across adverse event reports?"
2. "What root causes recur across multiple RCA documents?"
3. "Which departments are most central to sentinel event clusters?"

Also rehearse one refusal ("What is the total financial cost of
these adverse events?") to showcase the honesty behavior, and one
drill-down ("Tell me more about the vancomycin incidents") to show
the force-directed graph updating.

## 9. Teardown (after the demo, to stop billing)

```bash
gcloud run services delete capstone-backend  --region us-central1 --quiet
gcloud run services delete capstone-frontend --region us-central1 --quiet
# Vector Search index + endpoint:
cd $REPO/backend && uv run python scripts/06_teardown.py
```

## Troubleshooting

- **`PERMISSION_DENIED` from Vertex AI at request time**: the runtime
  service account is missing `roles/aiplatform.user`. Re-run the
  binding in step 3.
- **`FileNotFoundError: data/vector_search_ids.json`**: the backend
  image didn't get the `data/` directory. Confirm `data/` is present
  in the ZIP you unzipped (see `ls $REPO/data`) and that
  `backend/Dockerfile` still contains the `COPY data /srv/capstone/data`
  line.
- **Frontend gets 502 proxying to backend**: `BACKEND_URL` env var
  on the frontend service points to the wrong URL or includes a
  trailing slash. Re-deploy with `--update-env-vars BACKEND_URL=...`.
- **Cold-start latency**: ensure `--min-instances 1` on backend.
