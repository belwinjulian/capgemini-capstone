# Deploying to Google Cloud (all-GCP, Cloud Run) — Windows / PowerShell

Runbook for deploying the Patient Safety Intelligence assistant to
Cloud Run from a **Windows** Capgemini laptop, using **PowerShell**.
Copy-paste the commands in order. No AI tooling required.

> If you prefer Git Bash or WSL, the commands here translate almost
> directly — just swap `$env:VAR` for `export VAR=` and backtick (`` ` ``)
> line continuations for backslash (`\`).

## Assumptions

- GCP project: `capgemini-capstone-494100` (already has Vertex AI,
  Vector Search, and GCS set up from earlier ingestion).
- Active gcloud identity: `belwin.julian-robert-raj@capgemini.com`.
- Region: `us-central1` throughout.
- Repo ZIP downloaded from GitHub and unzipped somewhere. Referred
  to below as `$REPO` (e.g. `C:\Users\you\Downloads\capgemini-capstone-main`).

Data files (`data\chunks.json`, `data\graph.pkl`,
`data\vector_search_ids.json`, etc.) are checked into the repo so
the backend image is fully self-contained.

## 0. One-time tool setup

Install:

- **Google Cloud CLI for Windows** — <https://cloud.google.com/sdk/docs/install>
  (run `GoogleCloudSDKInstaller.exe`, accept defaults, restart
  PowerShell afterward).

You do **not** need Docker on the laptop — Cloud Build runs in GCP.

Open a fresh **PowerShell** window and run:

```powershell
gcloud auth login                                   # opens browser for SSO
gcloud auth application-default login               # for local smoke tests only
gcloud config set project capgemini-capstone-494100
gcloud config set run/region us-central1
gcloud config set artifacts/location us-central1
```

Enable required APIs (idempotent):

```powershell
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  aiplatform.googleapis.com `
  secretmanager.googleapis.com `
  iam.googleapis.com
```

Set a variable for the rest of the session so paths work:

```powershell
$REPO = "C:\path\to\capgemini-capstone-main"   # adjust to where you unzipped
cd $REPO
```

## 1. Create the Artifact Registry repo

```powershell
gcloud artifacts repositories create capstone-images `
  --repository-format=docker `
  --location=us-central1 `
  --description="Capstone Cloud Run images"
```

If it already exists you'll get `ALREADY_EXISTS` — safe to ignore.

## 2. Create the runtime service account

```powershell
gcloud iam service-accounts create capstone-runtime `
  --display-name="Cloud Run runtime for capstone"

$PROJECT = "capgemini-capstone-494100"
$SA      = "capstone-runtime@$PROJECT.iam.gserviceaccount.com"

foreach ($role in @(
    "roles/aiplatform.user",
    "roles/storage.objectViewer",
    "roles/secretmanager.secretAccessor")) {
  gcloud projects add-iam-policy-binding $PROJECT `
    --member="serviceAccount:$SA" --role="$role"
}
```

## 3. Build + push the backend image

Run from the repo root (`$REPO`). The backend Dockerfile expects to
see both `backend\` and `data\` in its build context, so build
context = repo root.

```powershell
cd $REPO

gcloud builds submit --config cloudbuild.backend.yaml .
```

First build takes ~5 min. The `cloudbuild.backend.yaml` at the repo
root tells Cloud Build to use `backend/Dockerfile` while keeping the
repo root as build context (so `data/` is available).

## 4. Deploy the backend to Cloud Run

```powershell
gcloud run deploy capstone-backend `
  --image "us-central1-docker.pkg.dev/capgemini-capstone-494100/capstone-images/backend:v1" `
  --service-account "capstone-runtime@capgemini-capstone-494100.iam.gserviceaccount.com" `
  --region us-central1 `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --concurrency 20 `
  --min-instances 1 `
  --set-env-vars "GOOGLE_CLOUD_PROJECT=capgemini-capstone-494100,VERTEX_AI_LOCATION=us-central1"
```

`--min-instances 1` keeps one warm — Vertex AI Vector Search clients
take ~15 s to initialize on cold start, which ruins a live demo.

Capture the backend URL:

```powershell
$BACKEND_URL = gcloud run services describe capstone-backend `
  --region us-central1 --format="value(status.url)"
Write-Host "Backend URL: $BACKEND_URL"

# Smoke test — should stream 'data: {...}' SSE events
$body = '{"question":"Which medications appear most frequently across adverse event reports?"}'
Invoke-WebRequest -Method Post `
  -Uri "$BACKEND_URL/api/chat" `
  -ContentType "application/json" `
  -Body $body | Select-Object -ExpandProperty Content | Select-Object -First 1500
```

If you get a 401/403, re-check the IAM bindings in step 2.

## 5. Build + push the frontend image

```powershell
cd $REPO

gcloud builds submit --config cloudbuild.frontend.yaml .
```

## 6. Deploy the frontend to Cloud Run

```powershell
gcloud run deploy capstone-frontend `
  --image "us-central1-docker.pkg.dev/capgemini-capstone-494100/capstone-images/frontend:v1" `
  --region us-central1 `
  --allow-unauthenticated `
  --memory 512Mi `
  --cpu 1 `
  --concurrency 80 `
  --min-instances 1 `
  --set-env-vars "BACKEND_URL=$BACKEND_URL"
```

Capture the frontend URL and open it:

```powershell
$FRONTEND_URL = gcloud run services describe capstone-frontend `
  --region us-central1 --format="value(status.url)"
Write-Host "Frontend URL: $FRONTEND_URL"
Start-Process $FRONTEND_URL
```

## 7. Demo checklist

Click each of the three demo questions once, right before presenting,
to warm the instances:

1. "Which medications appear most frequently across adverse event reports?"
2. "What root causes recur across multiple RCA documents?"
3. "Which departments are most central to sentinel event clusters?"

Also rehearse:

- One refusal: "What is the total financial cost of these adverse events?"
  — shows the honesty behavior.
- One drill-down: "Tell me more about the vancomycin incidents."
  — shows the force-directed graph re-populating.

## 8. Teardown (after the demo, to stop billing)

```powershell
gcloud run services delete capstone-backend  --region us-central1 --quiet
gcloud run services delete capstone-frontend --region us-central1 --quiet
```

The Vertex AI Vector Search index + endpoint are the expensive
resources (~$3/hour for the endpoint). If you also want to kill
those from Windows, the scripts/06_teardown.py uses pure Python and
works on Windows — but you'd need Python 3.11+ installed:

```powershell
cd $REPO\backend
pip install uv
uv sync
uv run python scripts/06_teardown.py
```

## Troubleshooting

- **`gcloud` not recognized**: restart PowerShell after installing
  the SDK, or add `C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin`
  to your `PATH`.
- **`PERMISSION_DENIED` from Vertex AI at request time**: the
  runtime service account is missing `roles/aiplatform.user`.
  Re-run the binding loop in step 2.
- **`FileNotFoundError: data/vector_search_ids.json` in Cloud Run
  logs**: the backend image didn't get the `data\` directory.
  Confirm `dir $REPO\data` shows the files and that
  `backend/Dockerfile` still contains the `COPY data /srv/capstone/data`
  line.
- **Frontend returns 502**: the `BACKEND_URL` env var on the
  frontend service is wrong or has a trailing slash. Re-deploy:

  ```powershell
  gcloud run services update capstone-frontend `
    --region us-central1 `
    --update-env-vars "BACKEND_URL=$BACKEND_URL"
  ```

- **Cloud Build fails with "context exceeds size limit"**: the
  `.gcloudignore` at repo root may be missing. Confirm with
  `dir -Force $REPO\.gcloudignore`. It should exclude
  `node_modules`, `.venv`, `.next`, and `corpus/`.
- **PowerShell line-continuation gotcha**: the backtick (`` ` ``)
  must be the **last** character on the line — no trailing spaces.
  If a command errors with "unexpected token", that's usually why.
