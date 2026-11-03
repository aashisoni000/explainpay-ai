# ExplainPay

Financial trust intelligence: transaction fraud classification, actual SHAP
explanations, URL phishing classification, optional threat intelligence,
PostgreSQL-backed investigations, and downloadable PDF reports.

The original Geist/Three.js shader homepage is preserved. The frontend remains
at the repository root; the Python API and ML pipeline live in `backend/`.

**Educational decision support only.** A prediction is not proof of fraud.
Anomalies, phishing predictions, and external threat findings are distinct.
No known detections does not establish safety. This application does not replace
professional fraud investigation or cybersecurity services.

## How to run (existing local setup)

**`npm run dev` starts only the frontend. PostgreSQL and the Python API must
also be running.** Run commands below from the repository root.
Dependencies, database migrations, and models only need setup once; do not
retrain models every time you start the app.

### 1. Start PostgreSQL

Use the database installation configured in your `.env`:

```bash
# Current macOS Homebrew setup
brew services start postgresql@16
pg_isready
```

If you configured the Docker alternative instead:

```bash
docker compose up -d --wait postgres
```

Use one database setup, not both. `DATABASE_URL` must point to that database.

### 2. Terminal 1: start the backend

```bash
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend \
  --host 127.0.0.1 --port 8001
```

Leave this terminal running. API documentation:
http://127.0.0.1:8001/docs.

### 3. Terminal 2: start the frontend

```bash
npm run dev
```

Leave this terminal running and open **the URL printed by Next.js**, normally
http://localhost:3000. If port 3000 is occupied, Next.js may select another port.
Do not open an older frontend instance by mistake.

The relevant `.env` values are:

```dotenv
NEXT_PUBLIC_API_URL=/backend
BACKEND_API_URL=http://127.0.0.1:8001
```

The frontend forwards `/backend/api/...` to Python. Do not put a direct localhost
API URL in the browser configuration unless deliberately bypassing this proxy.

### 4. Verify everything is ready

In another terminal:

```bash
# Python API must return {"status":"ok"}
curl --fail http://127.0.0.1:8001/api/health

# Change port 3000 here if Next.js printed a different frontend port.
curl --fail http://localhost:3000/backend/api/system/status
```

System status should report `database.available: true`,
`models.fraud.available: true`, and `models.phishing.available: true`.
Optional threat providers can be `not_configured` or `disabled`.
The same information is visible at `/settings`.

To try transaction analysis, upload
`data/processed/ulb_sample_transactions.csv`, not the full training CSV.
Generate this local sample using the command in [Workflows and API](#workflows-and-api)
if it is missing.

### Stopping and restarting

Press `Ctrl+C` in each application terminal to stop it. Next time, ensure
PostgreSQL is running and repeat the two application commands. Existing models
and saved investigations remain on disk/in PostgreSQL.

## Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [First-time setup](#first-time-setup)
- [Real Kaggle datasets](#real-kaggle-datasets)
- [Training](#training)
- [Production frontend and container](#production-frontend-and-container)
- [Workflows and API](#workflows-and-api)
- [Troubleshooting](#troubleshooting)
- [Validation](#validation)
- [Verified local dataset evaluation](#verified-local-dataset-evaluation)
- [Limitations and deployment](#limitations-and-deployment)

## Architecture

```text
Next.js 16 / TypeScript / Tailwind 4 / Lucide
                  | typed REST requests
FastAPI / Pydantic / SQLAlchemy / Alembic
       |                  |                 |
PostgreSQL 16      local trained models    optional trusted APIs
                  sklearn/XGBoost/SHAP    VirusTotal/Web Risk/RDAP
```

```text
app/                  Homepage and investigation routes
components/           Reusable UI and investigation components
lib/                  Typed API access
backend/app/          API, persistence, services, and ML
backend/app/ml/       Shared preprocessing, training, inference, SHAP
backend/tests/        API, database, report, validation, and ML tests
data/raw/transactions/creditcard.csv
data/raw/websites/phishing_features.csv
data/models/          Ignored artifacts and actual evaluation JSON
docker-compose.yml    Local PostgreSQL only
CLAUDE.md             Project-specific engineering rules
```

## Prerequisites

- Node.js 20.9+ and npm.
- Python 3.12 (tested); `uv` is optional.
- PostgreSQL 16+, or Docker Compose.
- Network access on the initial Next.js build to retrieve Geist.

## First-time setup

Skip this section when dependencies, `.env`, migrations, and models already
exist. **Do not overwrite an existing `.env`.**

```bash
npm ci
# Only for a new checkout without .env:
cp -n .env.example .env
mkdir -p data/raw/transactions data/raw/websites
uv venv --python 3.12 backend/.venv
uv pip install --python backend/.venv/bin/python -r backend/requirements.lock
```

Without `uv`, use `python3.12 -m venv backend/.venv`, then
`backend/.venv/bin/python -m pip install -r backend/requirements.lock`.
The lock file captures the tested backend dependency versions. Never commit
`.env`, Kaggle credentials, raw data, generated reports, or model binaries.

### PostgreSQL

Set `POSTGRES_USER`, a strong `POSTGRES_PASSWORD`, and `POSTGRES_DB` in `.env`.
Compose binds PostgreSQL to loopback port 5433 by default:

```bash
docker compose up -d --wait postgres
```

Set `DATABASE_URL` to
`postgresql+psycopg://<user>:<URL-encoded-password>@localhost:5433/<database>`.
For an existing local PostgreSQL installation, create a dedicated database and
provide its connection URL instead. Do not point tests at a production database.

Apply migrations before starting the API:

```bash
backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/python -m alembic -c backend/alembic.ini current
```

The application does not silently create tables on startup.

### Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection URL |
| `NEXT_PUBLIC_API_URL` | Browser API prefix; default `/backend` (same-origin proxy) |
| `BACKEND_API_URL` | Server-side proxy target; default `http://127.0.0.1:8001` |
| `CORS_ORIGINS` | JSON array of allowed frontend origins |
| `MODEL_DIR` | Trusted local model directory; default `data/models` |
| `STORAGE_DIR` | Generated report storage |
| `MAX_UPLOAD_BYTES` | Upload limit; default 10 MiB |
| `MAX_UPLOAD_ROWS` | CSV row limit; default 5,000 |
| `VIRUSTOTAL_API_KEY` | Optional VirusTotal URL intelligence |
| `GOOGLE_WEBRISK_API_KEY` | Optional Google Web Risk |
| `RDAP_ENABLED` | Opt into domain registration lookup |
| `TEST_DATABASE_URL` | Dedicated PostgreSQL database for integration tests |

Changing either API URL requires restarting development or rebuilding production.
The browser uses `/backend/api/...` on the frontend origin; Next.js proxies it
to FastAPI. This avoids browser localhost, mixed-content, and CORS issues when
accessing the frontend through a forwarded port. FastAPI must still be running.
API keys belong only in the backend environment, never `NEXT_PUBLIC_*`.
Optional services report not-configured/unavailable explicitly.

## Real Kaggle datasets

The application does **not** download datasets automatically.

1. [ULB credit card fraud](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud):
   place `creditcard.csv` in `data/raw/transactions/`.
2. [Phishing URLs with extracted features](https://www.kaggle.com/datasets/victusadi/phishing-urls-dataset-with-extracted-features):
   place the actual CSV in `data/raw/websites/`. Use `--path` if its name differs
   from `phishing_features.csv`.

If using the optional Kaggle CLI, install it separately, configure your Kaggle
token through its official credential mechanism, and never put `kaggle.json`
in Git. Generate an API token in Kaggle account settings and set
`KAGGLE_API_TOKEN` in your shell (or follow the CLI's legacy credential-file
instructions). Do not paste credentials into source files. Example commands
after authenticating:

```bash
uvx --from kaggle kaggle datasets download -d mlg-ulb/creditcardfraud \
  -p data/raw/transactions --unzip
uvx --from kaggle kaggle datasets download \
  -d victusadi/phishing-urls-dataset-with-extracted-features \
  -p data/raw/websites --unzip
```

Comply with the dataset source's license and access requirements.

## Training

Run from the repository root. Inspect **before** selecting phishing columns or
label encodings:

```bash
export PYTHONPATH=backend
backend/.venv/bin/python -m app.ml.train fraud --inspect
backend/.venv/bin/python -m app.ml.train phishing --inspect \
  --path data/raw/websites/phishing_features.csv
```

Train the fraud model:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.ml.train fraud
```

For the inspected `phishing_features.csv`, the publisher explicitly documents
`url`, `label`, `1 = Phishing`, and `0 = Benign`. Other datasets require fresh
schema and label verification:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m app.ml.train phishing \
  --path data/raw/websites/phishing_features.csv \
  --url-column url --target-column label \
  --positive-label 1 --negative-label 0 \
  --label-source https://www.kaggle.com/datasets/victusadi/phishing-urls-dataset-with-extracted-features
```

Each command writes `<kind>.joblib` and `<kind>.metrics.json` to `data/models/`.
Restart the backend after retraining; loaded artifacts are cached. Load only
trusted artifacts produced locally: Joblib files can execute Python code.
Missing or incompatible models produce explicit HTTP 503 responses, never
invented predictions.

### Scientific methodology

- Validate schema, missing values, finite values, duplicates, and class labels.
- ULB inputs: `Time`, `V1` through `V28`, `Amount`; target: `Class`.
  PCA features have no invented human-readable financial interpretation.
- Deduplicate identical transaction features and normalized URLs **before**
  splitting; conflicting duplicate labels stop training.
- Phishing inference uses 15 lexical features extracted by the exact same
  function used in training. Inaccessible webpage features are never used.
  Invalid public URLs are removed and their count is reported.
- Seeded, stratified 60% train / 20% validation / 20% test split.
- Compare balanced Logistic Regression with XGBoost using training-only
  `scale_pos_weight`; no oversampling or test-set preprocessing fit.
- Choose the model using validation average precision (PR-AUC); choose its
  threshold using maximum validation F1. The test set is not used for selection.
- Report precision, recall, F1, PR-AUC, ROC-AUC, confusion matrix, false-positive
  rate, and detection rate. Accuracy is not the primary measure.
- SHAP explains actual model log-odds. Contributions are **not** probability
  percentage points. Base value plus all contributions reconstructs log-odds.
- Isolation Forest is fit only on legitimate training transactions. Its score
  is an independent anomaly indicator, not a second fraud label.
- Persist source SHA-256, cleaning counts, label mapping, split sizes, versions,
  chosen threshold, and real evaluation results alongside each model.
- Probability outputs are model estimates, not calibrated guarantees. Random
  stratified evaluation does not establish temporal or unseen-domain validity.

Risk is `low` below the learned threshold, `medium` when flagged, and `high`
when flagged with estimated probability at least 0.8. Risk is triage, not proof.

Real artifacts and evaluation JSON are generated locally and excluded from Git;
they are not bundled in the repository. Unit tests use explicitly
labelled temporary synthetic fixtures to verify mechanics; those are not
Kaggle training results and are never copied into production artifacts.

## Production frontend and container

Instead of `npm run dev`, use:

```bash
npm run build
npm run start
```

PostgreSQL and the Python API still need to run separately. Do not run
`npm run dev` and `npm run start` on the same frontend port.

The optional backend image can be built with
`docker build -f backend/Dockerfile -t explainpay-api .`.
Mount trusted models and report storage and supply environment variables at
runtime; neither datasets nor credentials are copied into the image.

## Workflows and API

- `/transactions`: CSV upload, validated preview, batch analysis, filtering,
  sorting, pagination, actual distributions, individual SHAP explanations.
- `/website-scanner`: URL validation, local phishing prediction, explanations,
  optional-provider findings, persisted scan history.
- `/investigations`: PostgreSQL-backed investigation history.
- `/reports`: PDF exports containing stored results, evidence, and limitations.
- `/settings`: actual service availability and trained-model evaluation.

CSV uploads accept at most 5,000 rows and 10 MiB by default. Include all 30
numeric ULB feature columns. `Class` is optional and is never an inference
feature. A supplied `merchant_url` can link to a website investigation; the
ULB dataset does not identify original merchants. Do not invent merchant URLs.
Generate a small upload from your local real data instead of submitting the
entire training dataset.

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/make_transaction_sample.py
```

This writes ten actual labelled ULB rows and a provenance note under ignored
`data/processed/`. Source labels are not predictions; these demonstration rows
must not be treated as held-out model evaluation.

OpenAPI at `/docs` describes request and response schemas. Main endpoints:

```text
GET  /api/health                     GET  /api/system/status
POST /api/transactions/upload        POST /api/transactions/analyze
POST /api/transactions/predict       GET  /api/transactions/history
GET  /api/transactions/metrics       GET  /api/transactions/{id}
GET  /api/transactions/uploads/{id}
POST /api/websites/scan              GET  /api/websites/history
GET  /api/websites/{id}
GET  /api/websites/metrics
GET  /api/investigations             GET  /api/investigations/{id}
GET  /api/reports                    POST /api/reports/generate
GET  /api/reports/{id}/download
```

Health checks do not imply model availability; inspect system status separately.
External providers use fixed trusted API hosts with timeouts, never the submitted
website itself. An unconfigured check is not a negative finding.

## Troubleshooting

| Symptom | Check / fix |
|---|---|
| "Cannot reach the ExplainPay API" | Start Python in Terminal 1. Check direct API health, then `/backend/api/health` on the frontend URL. Keep both terminals open. |
| `/backend/api/...` returns 502/500 | The frontend proxy cannot reach Python. Confirm `BACKEND_API_URL` matches Uvicorn's host and port. |
| API returns 404 on port 8000 | This project uses port **8001** by default; port 8000 may belong to another application. |
| Database unavailable / connection refused | Start PostgreSQL and verify `DATABASE_URL`. Apply Alembic migrations during first-time setup. |
| Model unavailable (503) | Train the missing model using [Training](#training), confirm `MODEL_DIR`, then restart Python. |
| Address already in use | Reuse the correct running instance or stop it in its own terminal. If changing the API port, update `BACKEND_API_URL` and restart the frontend. |
| Old error remains after configuration changes | Restart the frontend and reload the page; public environment values and rewrites are loaded at startup/build time. |
| CSV rejected as too large | Upload the generated sample or another valid CSV within the 10 MiB / 5,000-row limits. |
| Provider is not configured | Optional API keys are absent; local model prediction still works. This does not mean a website is safe. |

Never kill unrelated services or remove saved data to resolve a port conflict.

## Validation

```bash
npm run lint
npx tsc --noEmit
npm run build
node --test frontend-tests/workspace.test.mjs
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q
backend/.venv/bin/ruff check backend
```

Database tests require a **separate disposable** PostgreSQL database:

```bash
createdb explainpay_test
TEST_DATABASE_URL='postgresql+psycopg:///explainpay_test?host=/tmp' \
  PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q
```

Tests without a configured integration database may skip database-dependent
cases; a skipped test is not a verified persistence flow.

Playwright tests expect the frontend on `http://127.0.0.1:3000`.
Start the API against a disposable test database and the frontend separately:

```bash
# Apply migrations to the test database.
DATABASE_URL='postgresql+psycopg:///explainpay_test?host=/tmp' \
  backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head

# Test API terminal (stop any existing ExplainPay API on port 8001 first).
DATABASE_URL='postgresql+psycopg:///explainpay_test?host=/tmp' \
  backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend \
  --host 127.0.0.1 --port 8001

# Separate test-runner terminal; frontend must already be running.
E2E_API_URL=http://127.0.0.1:8001 npm run test:e2e
```

These database URLs are macOS local socket examples; use your test database's
actual credentials/host for Docker or other installations.
If Chromium is missing, run `npx playwright install chromium`.
Override `E2E_BASE_URL` for a different frontend origin and `E2E_API_URL`
for a different API origin.
Workspace browser tests create an explicitly labelled synthetic upload to test
validation/persistence. Run the API against a disposable test database for
these tests. Workspace tests check the actual model availability rather than
substituting responses. The real-model suite requires local trained artifacts
and the generated ULB sample; it verifies predictions, SHAP views, persisted
history, PDF bytes, and both evaluation reports. Missing-model errors are also
covered by backend tests.

## Verified local dataset evaluation

Both actual user-downloaded datasets were inspected and trained on 2026-11-03.
XGBoost was selected by validation PR-AUC for both tasks; thresholds were selected
by validation F1, not tuned using the test results below.

| Held-out test metric | Transaction fraud | URL phishing |
|---|---:|---:|
| Precision | 0.898734 | 0.998195 |
| Recall | 0.747368 | 0.998487 |
| F1 | 0.816092 | 0.998341 |
| PR-AUC (average precision) | 0.800049 | 0.999991 |
| ROC-AUC | 0.967398 | 0.998940 |
| False-positive rate | 0.000141 | 0.225610 |
| Threshold | 0.968706 | 0.014913 |

Fraud source: 284,807 rows; 1,081 duplicate inputs removed.
Phishing source: 160,064 rows; 56,678 unsupported URLs removed (55,814 used
nonstandard ports), then 122 normalized duplicates removed, leaving 102,444
phishing and only 820 benign URLs. The 821 missing pre-extracted `tld` values
are irrelevant because training recomputes all lexical features from the URL.

**Phishing limitations are material:** the held-out benign false-positive rate is
22.56% (37 of 164 benign URLs), despite the very high positive-class metrics.
The approximately 99.2% phishing prevalence makes PR-AUC/F1 look unusually strong.
These results do not establish broad real-world website trustworthiness.
Random URL splits may share domains; nonstandard-port sites are outside supported
inference coverage. Original data was not altered, balanced artificially, or
mixed with synthetic training examples.

Full reproducible results, confusion matrices, baseline comparisons, input
hashes, rejection reasons, and limitations are saved under ignored
`data/models/*.metrics.json` and displayed on `/settings`.

## Limitations and deployment

- On a fresh checkout, download the datasets and train both models before
  prediction. Generated local artifacts are intentionally not committed.
- External providers require keys/network access; RDAP is opt-in.
- No authentication is included in this academic local demo. Bind to loopback.
  Before public deployment add identity/authorization, rate limiting, TLS,
  retention/deletion policies, background jobs, and a production secrets manager.
- Batch analysis is synchronous and bounded. Large-scale processing is outside
  the initial local application scope.
- Inputs required for pending analyses and explanations are persisted. Do not
  upload real sensitive customer data without a reviewed retention policy.
- Docker availability is separate from application correctness; a local
  PostgreSQL installation can run the exact same migrations and integration tests.
