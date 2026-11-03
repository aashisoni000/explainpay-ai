# Final evidence audit

## What was extracted

- Both actual source CSV schemas, raw/cleaned row counts, class counts and imbalance,
  source duplicates, invalid URL rejection reasons, missingness and dtypes.
- All numerical mean, median, sample standard deviation, minimum, maximum and
  quartiles; per-class equivalents; full-range 50-bin histograms; Pearson matrices.
- Exact stratified 60/20/20 split membership, seed 42, feature order, fitted scaler
  checks, training/background checks and saved model/data SHA-256 provenance.
- Historical validation and test metrics for all four supervised candidates, with
  accuracy, specificity, FPR and FNR derived from actual confusion counts.
- Reloaded selected-model held-out probabilities, confusion matrices, ROC and
  precision-recall points; their saved metrics were reproduced without retraining.
- Selected-model XGBoost gain, full exposed estimator parameters, resolved booster
  configurations, 512-row stratified SHAP samples and one actual TP/FP/FN/TN case
  per task. SHAP was checked against the selected model's raw-margin predictions.
- Actual implementation, deployment boundaries, architecture and experimental
  limitations. See [implementation audit](implementation_audit.md),
  [architecture](architecture.md) and [technical narrative](technical_content.md).

All statistics and feature definitions are in [dataset_summary.md](dataset_summary.md).
The [pack index](README.md) explains every asset and the reproduction commands.
Per-row score, split and SHAP exports exist locally but are intentionally ignored by
Git. Raw CSVs and model binaries were not added to Git.

## Findings worth highlighting

1. **Real, reproducible dual-task project:** independent fraud and phishing models,
   validation-selected algorithms/thresholds, fitted preprocessing reused at
   inference, saved artifacts, SHAP and persistent application workflows.
2. **Fraud performance:** selected XGBoost test AP 0.800049, ROC-AUC 0.967398,
   precision 0.898734 and recall 0.747368; 71 TP, 8 FP, 24 FN and 56,643 TN.
   The test positive prevalence is only 95/56,746. Accuracy alone is misleading.
3. **Phishing metrics need context:** test AP 0.999991 is measured against a
   0.992059 positive-prevalence baseline. Only 164 benign test URLs exist.
   XGBoost falsely flags 37 of them: **22.560976% benign FPR**.
4. **Different criteria reveal a trade-off:** phishing Logistic Regression has
   lower recall but only 20/164 benign false positives, **12.195122% FPR**.
   Do not retrospectively select or tune a model using the test set.
5. **Generalisation boundary:** 13,840/20,653 phishing test rows
   (**67.012056%**) share an exact hostname with training. The current score is
   not an unseen-domain evaluation. Fraud train and test time ranges also overlap.
6. **Material cleaning effect:** 56,678 phishing rows fail the production URL
   validator, including 55,814 nonstandard-port URLs; all rejected rows are labelled
   phishing. Cleaning changes the evaluated population.
7. **Interpretation without invented semantics:** V1–V28 remain anonymous PCA
   components. The fraud global SHAP leaders are V4, V14 and V8; the phishing
   leaders are URL length, path length and URL entropy in this sampled population.

## Inconsistencies and limitations found

These are documented findings, not application changes:

| Finding | Consequence / next experiment |
|---|---|
| Random URL split with repeated hostnames | Add domain-grouped holdout; consider public-suffix-aware grouping. |
| Random fraud split with overlapping `Time` | Add a chronological holdout without fitting preprocessing on future rows. |
| Phishing labels heavily favour positives | Report benign specificity/FPR alongside precision, recall and AP; add representative benign data. |
| Rejection disproportionately removes phishing rows | Report exclusions; benchmark any broader input policy as a separate experiment. |
| Original losing Logistic Regression estimators were not saved | Historical aggregate results exist, but their original curves, coefficients and SHAP cannot be extracted. |
| No original training-size/loss history | Do not label reconstructed learning curves as historical training records. |
| Validation threshold maximises F1, not a false-positive budget | Define deployment costs or a target FPR and select a threshold on validation data only. |
| No calibration evaluation | Model scores must not be presented as certified probabilities of real-world harm. |
| Fraud threshold 0.968706 exceeds the 0.8 high-risk boundary | The current rule makes the fraud medium-risk band unreachable. |
| `fraud_detection_rate` metric key reused for phishing | Interpret it as positive-class recall, not a separate measurement. |
| `subdomain_count` is hostname-label count minus two | It is not a public-suffix-aware registrable-domain calculation. |
| SHAP global sample follows dataset class prevalence | Fraud has 1 positive/512 rows; phishing has 4 benign/512. Add class-conditioned summaries before minority-class claims. |
| Lexical phishing model, not downloaded site inspection | It cannot verify page content, TLS validity, ownership, or actual malicious intent. |
| Optional threat providers not configured in the inspected environment | Do not claim live threat intelligence contributed to these model evaluations. |
| Isolation Forest has no held-out anomaly benchmark | Anomaly scores are supporting signals, not measured fraud-detection performance. |
| Local demonstration, not production authentication | Do not expose financial investigation endpoints as a public service unchanged. |

No bugs were silently fixed in the existing application during this documentation task.

## Missing original results and exact next commands

Run commands from the repository root using the existing backend environment.

### Recover missing baseline curve data as a clearly labelled reconstruction

```bash
backend/.venv/bin/python reports/ml_analysis/missing_experiments.py recover-baselines
```

This fits only the unsaved Logistic Regression baselines using the original
preparation/split protocol. It checks reconstructed validation/test metrics against
historical results and writes new, explicitly labelled outputs under
`new_experiments/`. It does not modify deployed artifacts. This optional command
was **not executed** for the report. Exact recovery remains conditional on its
metric-agreement checks.

### Run a new learning-curve experiment

```bash
backend/.venv/bin/python reports/ml_analysis/missing_experiments.py learning-curves
```

This performs new training-only, three-fold average-precision experiments across
five training sizes, using fixed selected hyperparameters. It can take substantial
time and was **not executed**. Outputs are CSVs, not an original training log or
automatically generated publication figures.

### Reproduce all available evidence and publication figures

```bash
backend/.venv/bin/python -m pip install -r reports/ml_analysis/requirements.lock
PYTHONPATH=backend backend/.venv/bin/python reports/ml_analysis/analyze.py
backend/.venv/bin/python reports/ml_analysis/write_summaries.py
backend/.venv/bin/python reports/ml_analysis/graph_generation.py
backend/.venv/bin/python -m pytest reports/ml_analysis/test_analysis.py -q
```

The private raw CSVs and existing trained artifacts must be present. The extraction
commands are offline and do not retrain selected models.

### Experiments not implemented by a command

Domain-grouped/temporal holdouts, confidence intervals, calibration, deployment-cost
thresholds, externally representative validation and anomaly benchmarking require
new experiment code and, in some cases, additional labelled data. There is no
existing trustworthy command that produces those results; none were invented here.
Live threat-provider validation also requires separately configured credentials
and quota, and is not part of this offline model evaluation.

## Graph availability

The actual generated figure inventory and captions are in
[figures/captions.csv](figures/captions.csv).
Only selected-model ROC/PR curves and SHAP are available from the saved estimators.
Both candidates' confusion matrices and metric comparisons use their actual saved
aggregate evaluations. Missing original baseline curves, baseline explanations and
learning/loss curves are deliberately omitted rather than simulated.

## Verification scope

The research tests check exported counts, split disjointness, histogram conservation,
metric identities, curve conventions, SHAP aggregation/additivity and unchanged
selected-artifact hashes. The extraction itself additionally checks original data
hashes, fitted preprocessing, exact split/background reproduction and saved metrics.
Application code, model artifacts and datasets were not modified; this task did not
repeat unrelated frontend/backend application suites.
