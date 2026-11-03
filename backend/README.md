# ExplainPay API

This is a localhost academic decision-support API. It intentionally has no login:
do not expose it to untrusted networks without authentication, rate limiting, and
appropriate operational controls. The Next.js application is independent.

## Database and startup

Set `DATABASE_URL` to a PostgreSQL connection URI in the environment or the
repository-root `.env`. Credentials must be supplied by the operator.
Plain `postgresql://` URIs are automatically configured to use psycopg.

From `backend/`, after installing the project's dependency manifest:

```sh
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Schema creation is performed exclusively through Alembic. Startup does not create
tables or silently replace a failed database with SQLite or in-memory storage.
`GET /api/health` is a liveness check; `GET /api/system/status` reports database,
trained-model, and optional provider availability. `/docs` provides the API schema.

## Evidence and upload behavior

- CSV uploads must be UTF-8, have a `.csv` filename, and include `Time`,
  `V1` through `V28`, and `Amount`. Values must be finite numeric values;
  `Time` and `Amount` cannot be negative.
- Optional `merchant_url` is normalized and validated as a public HTTP(S) URL.
  `Class` and other extra input columns are ignored, never used as features,
  and never persisted. At most 64 columns and 5,000 data rows are accepted.
- `MAX_UPLOAD_BYTES` defaults to 10 MiB (configurable up to 50 MiB).
  `MAX_UPLOAD_ROWS` can lower, but not raise, the 5,000-row cap. Multipart body
  limits are enforced before form parsing; accepted raw files remain in memory.
  Raw CSV files are never saved. Only validated inference fields, sanitized
  filenames, and up to five preview rows are exposed.
- Upload creation is atomic. Analysis uses PostgreSQL row locks and one database
  transaction; retries return the same saved results without duplicate inserts.
  A model failure rolls back the entire batch.
- Prediction endpoints use real, locally trained artifacts through `app.ml.runtime`.
  Missing models return `503`; no placeholder probabilities or explanations are
  generated. Invalid inputs return `422`, oversized files `413`, and missing
  records `404`, all with `{"detail": "..."}` responses.
- Investigations, numerical predictions, SHAP contributions, optional anomaly
  results, website scans, findings, and PDF reports are stored in PostgreSQL.
  Response timestamps are normalized to UTC.

## Optional intelligence providers

`VIRUSTOTAL_API_KEY`, `GOOGLE_WEBRISK_API_KEY`, and `RDAP_ENABLED=true` enable
their respective adapters. Missing credentials and network failures are explicit
provider statuses, never interpreted as benign evidence.

Only the fixed HTTPS hosts `www.virustotal.com`, `webrisk.googleapis.com`,
`rdap.verisign.com` (for `.com`/`.net`), and `rdap.org` are contacted.
Submitted URLs are never fetched; VirusTotal uses
an existing URL-reputation lookup rather than submission. Redirects and
environment proxies are disabled. `PROVIDER_TIMEOUT_SECONDS` defaults to four
seconds per request and is bounded at 15 seconds. Adapters run concurrently.
RDAP registry referrals are reported unavailable rather than followed to an
arbitrary host. Provider details are allowlisted; credentials, contact records,
and raw provider bodies are not persisted.

PDF reports use only saved investigation evidence. They can explicitly describe
pending uploads without inventing predictions. All dynamic ReportLab text is
escaped; PDFs are stored as bytes, not filesystem paths.

## Tests

```sh
python -m pytest -q
TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost/TEST_DB' python -m pytest -q
```

Persistence/API integration tests require `TEST_DATABASE_URL` and skip when it is
unset. They use actual PostgreSQL, apply Alembic into a unique isolated schema,
and drop only that schema on teardown. The database role therefore needs schema
creation privileges. Tests never create application tables with `create_all`.
Coverage includes row-lock idempotency, rollback, migration/schema agreement,
constraints, invalid uploads, report downloads, and provider error handling.
Deterministic prediction doubles exist only inside API tests; ML tests separately
exercise the trained-artifact runtime.
