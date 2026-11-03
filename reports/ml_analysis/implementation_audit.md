# Implementation audit (repository-grounded)

## Scope audited

- Frontend app routes and UI modules.
- Backend API, ML runtime/training modules, persistence, reporting.
- Dataset/model artifacts presence and offline analysis exports.
- Environment wiring and runtime boundaries.

## Confirmed implemented modules

1. **Homepage visual direction**
   - Full-screen Three.js shader component with cleanup and responsiveness.
   - Two accessible navigation cards to transaction and website workflows.

2. **Transaction fraud workflow**
   - CSV ingestion and backend validation.
   - Prediction, thresholded decision, SHAP output.
   - Persistence and retrieval of investigations/history.
   - Report generation endpoint and downloadable PDF path.

3. **Website scanner workflow**
   - URL normalization and lexical feature extraction.
   - Prediction, thresholded decision, SHAP output.
   - Persistence and history endpoints.
   - Optional enrichment integration paths.

4. **ML training and artifact runtime**
   - Shared training orchestration.
   - Candidate model comparison and selection.
   - Saved selected artifacts loaded by runtime.
   - Feature-schema checks and deterministic seed usage.

5. **Database and migrations**
   - SQLAlchemy models + Alembic migration path.
   - PostgreSQL connectivity surfaced in system status endpoint.

6. **Testing and verification present in repository**
   - Backend/ML test suites.
   - Frontend unit tests.
   - Offline research extraction tests (`reports/ml_analysis/test_analysis.py`).

## Current ML evidence state (from generated exports)

- Selected model for both tasks: **XGBoost**, chosen by validation AP.
- Fraud and phishing candidate metrics exported for validation and test.
- ROC/PR points available for selected models.
- SHAP global and per-example evidence exported for both tasks.
- Dataset hashes and artifact hashes verified in manifest/test checks.

## Known constraints and gaps

- Original fitted losing Logistic Regression estimators were not persisted.
- No historical learning/loss curves saved during original training.
- No original calibration study or confidence intervals saved.
- Phishing evaluation uses random URL split with significant hostname overlap.
- Fraud split is random (not chronological holdout).
- Threat-provider enrichment remains optional and environment-dependent.

## Operational status expectations

For a fully working local run:
- Next.js frontend process must be running.
- FastAPI backend process must be running.
- PostgreSQL must be running.
- Local selected model artifacts must be present.

If only frontend is started, API calls will fail by design.
