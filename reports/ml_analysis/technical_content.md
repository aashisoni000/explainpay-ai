# ExplainPay: evidence-backed technical research content

## Abstract

ExplainPay is a locally deployed financial trust investigation system combining
transaction-fraud classification and URL-phishing classification with SHAP
explanations, investigation persistence, and evidence reports. The implemented
experiments compare class-weighted Logistic Regression and XGBoost using
stratified train/validation/test partitions, validation-only model/threshold
selection, and held-out testing. The ULB transaction source contains 284,807 rows;
the downloaded phishing source contains 160,064 rows. After the implemented
cleaning, 283,726 transaction rows and 103,264 URL rows remain.

Selected transaction XGBoost achieves test precision 0.898734, recall 0.747368,
F1 0.816092, average precision 0.800049 and ROC-AUC 0.967398. Selected URL
XGBoost achieves F1 0.998341 and average precision 0.999991, but falsely flags
37/164 benign test URLs (22.56%). The latter result must be interpreted against
approximately 99.2% phishing prevalence and substantial hostname overlap between
training and testing. This pack reports these limitations rather than treating
high aggregate scores as evidence of general website safety.

## 1. Introduction and problem statement

The implemented problem is to support two distinct investigations:

1. Estimate whether a transaction represented by the ULB numerical feature
   schema resembles labelled fraud, and expose its model contributions.
2. Estimate whether a validated public HTTP/HTTPS URL resembles labelled
   phishing URLs using features computable without fetching the submitted site.

A probability alone is insufficient for an investigator: the user needs a
decision threshold, feature evidence, provenance, provider availability, and a
saved report. Conversely, an explanation of a model's decision is not proof that
the decision is correct. ExplainPay separates those concepts in the interface.

The source transaction data does not expose original merchant names, locations,
devices, or transaction descriptions. The application cannot reconstruct those
attributes from V1-V28. Website classification is a different task and cannot
establish that a transaction is fraudulent.

## 2. Motivation, objectives, proposed solution

The project's engineering motivation is to connect a reproducible ML pipeline
to an actual usable investigation workflow rather than present disconnected
notebook metrics or mocked dashboard results.

Objectives:

- Validate actual input data and preserve train/inference feature consistency.
- Compare a linear baseline with a nonlinear boosting candidate.
- Handle class imbalance without resampling the complete dataset before split.
- Select models and decision thresholds without tuning on test outcomes.
- Explain individual predictions and aggregate contribution patterns.
- Distinguish supervised classification, anomaly scores, heuristics and external
  threat evidence.
- Save investigations and generate reports using actual results.
- Fail explicitly when models, the database or optional providers are unavailable.

The solution is a Next.js investigation frontend, a FastAPI service, PostgreSQL
persistence, locally serialized ML pipelines, and optional fixed-provider API
adapters. All implemented components and six architecture/workflow diagrams are
documented in [architecture.md](architecture.md); implementation evidence and
limitations are in [implementation_audit.md](implementation_audit.md).

## 3. Differentiating aspects and actual contribution

The defensible contribution is **integration and explainable investigation
workflow**, not a new classification algorithm or a claim of state-of-the-art
performance:

- Two separate evidence domains in one product with shared history and reports.
- SHAP explanations from the actual trained classifier, not generated financial
  narratives.
- An optional cross-layer link when a user actually supplies a merchant URL;
  no fabricated merchant identities for ULB rows.
- Transparent provider-availability states and no automatic visits to submitted
  websites.
- Independent Isolation Forest anomaly indication, not conflation with fraud.
- Consistent preprocessing at training and inference.
- A preserved cinematic Three.js homepage connected to actual application routes.

## 4. Research context and references boundary

The repository does not contain a systematic literature review or experiments
against published benchmarks. Therefore this report does not claim superiority
over external papers, production fraud systems or other phishing datasets.

The existing evidence supports the following methodological context:

- The ULB dataset source describes an extremely imbalanced binary fraud task
  with anonymized PCA features; accuracy is therefore inadequate in isolation.
- The phishing publisher documents lexical features and label encoding
  `1 = Phishing`, `0 = Benign`. The application's extractor recomputes its own
  features rather than trusting pre-extracted columns.
- Logistic Regression provides an interpretable linear baseline; XGBoost
  provides nonlinear tree interactions. This comparison is implemented, not an
  exhaustive hyperparameter study.
- SHAP's linear/tree explainers attribute the fitted model output relative to a
  background sample. Attribution is not causal evidence about real-world fraud.

See source/library URLs in References. Broader related-work claims require
additional literature collection and are intentionally not invented.

## 5. Datasets and preprocessing

Complete feature definitions, all column types, missing counts, means, medians,
standard deviations, ranges, class counts and split tables are in
[dataset_summary.md](dataset_summary.md). Exact values are in
[graph_data/](graph_data/).

### 5.1 ULB transactions

- Source: `mlg-ulb/creditcardfraud`; local `data/raw/transactions/creditcard.csv`.
- Raw: 284,807 rows, 31 columns, no missing values.
- Target: `Class`; legitimate 284,315, fraud 492.
- Inputs: `Time`, `V1` through `V28`, `Amount` (30 features).
- Raw legitimate/fraud ratio: 577.876:1.
- 1,081 duplicate inputs removed before splitting. Conflicting duplicate labels
  would abort preparation; none prevented this experiment.
- Cleaned: 283,253 legitimate and 473 fraudulent rows (283,726 total).
- Training/validation/test: 170,235 / 56,745 / 56,746.
- Class-1 examples in these partitions: 284 / 94 / 95.
- `Time` and `Amount` must be nonnegative and all values finite.

V1-V28 retain only component identifiers. They must not be renamed as location,
device fingerprint, merchant category or any other unavailable original feature.
Upstream ULB descriptions give transaction amounts in euros; arbitrary user
uploads do not carry a reliable currency field, and the interface conservatively
does not infer one.

### 5.2 URL phishing

- Source: `victusadi/phishing-urls-dataset-with-extracted-features`; actual local
  filename `phishing_features.csv`.
- Raw: 160,064 rows, 13 columns; 159,244 phishing and 820 benign URLs.
- Raw majority/minority ratio: 194.2:1, with **phishing as the majority**.
- Missing values: 821 in the source `tld`; URL/label values are present.
- Exact duplicate raw records: zero.
- 56,678 URLs rejected by the implemented public-URL policy, all from the
  phishing-labelled source subset:
  - 55,814 nonstandard HTTP/HTTPS ports.
  - 817 invalid/public-hostname failures.
  - 35 credential-bearing URLs.
  - 9 whitespace/control/backslash failures.
  - 3 empty/excessively long URLs.
- 122 duplicate normalized URLs removed.
- Cleaned: 102,444 phishing and 820 benign URLs, 103,264 total.
- Training/validation/test: 61,958 / 20,653 / 20,653.
- Benign examples: 492 / 164 / 164; phishing: 61,466 / 20,489 / 20,489.

The 15 actual inputs are `url_length`, `domain_length`, `dot_count`,
`subdomain_count`, `hyphen_count`, `digit_count`, `ip_hostname`, `https`,
`suspicious_tokens`, `parameter_count`, `suspicious_extension`, `url_entropy`,
`path_length`, `at_count`, and `encoded_count`.

The exact shared function is `backend/app/ml/urls.py::extract_features`.
The source's 11 precomputed features are not model inputs. This avoids
training on webpage/network features that cannot be reproduced from input URLs.
The same normalizer rejects private/reserved IPs, credentials and unsupported
ports at inference. Public DNS is not queried by the lexical extractor.

Important feature limitations: subdomain counting is not public-suffix-aware;
token matching uses substrings; `encoded_count` counts `%` characters, not valid
percent-escape sequences; HTTPS does not imply legitimacy.

## 6. ML methodology and experimental setup

### 6.1 Shared supervised protocol

The actual implementation is `backend/app/ml/train.py`.

1. Read and validate the source CSV and label mapping.
2. Inspect missing values, duplicates, types, and classes.
3. Clean/deduplicate before splitting and generate ordered numerical features.
4. Stratified 80% train+validation / 20% test split with seed 42.
5. Split train+validation 75% / 25%, yielding overall 60% / 20% / 20%.
6. Fit each `StandardScaler` on training rows only.
7. Fit the two candidates on training rows only.
8. Select each candidate's threshold by maximum validation F1.
9. Select the classifier with highest validation average precision.
10. Lock that selection; evaluate both candidates on the untouched test set.
11. Persist the selected pipeline, training-background sample, metrics, threshold,
    feature schema, source hash and version.

The analysis script reconstructs these exact partitions without retraining,
checks the fitted scaler's means and saved background, and reproduces all
selected-model validation/test metrics against the stored results. It aborts
if the raw source hash, cleaning, schema or metrics differ.

### 6.2 Logistic Regression

Pipeline: `StandardScaler()` then
`LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)`.
Unspecified parameters use the recorded scikit-learn version's defaults:
L2 regularization, `C=1`, `lbfgs` solver for this fitted configuration.
Only historical validation/test aggregates remain; the losing estimators were
not serialized. The analysis does not invent their coefficients or ROC points.

### 6.3 XGBoost

Pipeline: `StandardScaler()` then `XGBClassifier`:

| Parameter | Actual configuration |
|---|---|
| n_estimators | 200 |
| max_depth | 4 |
| learning_rate | 0.06 |
| subsample | 0.9 |
| colsample_bytree | 0.9 |
| scale_pos_weight | training negatives / training positives |
| eval_metric | logloss |
| tree_method | hist |
| n_jobs | 2 |
| random_state | 42 |

`scale_pos_weight` is about 598.419 for fraud (169,951/284) and 0.008004 for
phishing (492/61,466). A value below one is expected here because phishing is
the positive majority class. No SMOTE or other oversampling is implemented.
Scaling is unnecessary for tree splits but retained as part of the shared
pipeline; inference applies the same saved transform.

There is no cross-validated hyperparameter search, early-stopping evaluation
set, saved boosting-loss history, calibration step or learning-curve experiment.
Do not present `eval_metric="logloss"` as evidence that a learning curve exists.
Full fitted parameters are exported in `graph_data/*_parameters.json`.

### 6.4 Isolation Forest

Fraud additionally saves `IsolationForest(n_estimators=100, contamination=0.01,
max_samples=4096, random_state=42, n_jobs=2)` fit on legitimate training rows.
`decision_function < 0` becomes a separate anomaly flag.
No anomaly-specific validation metrics or ground-truth experiment were saved.
It is not a third supervised classifier and must not be included as if it has
fraud precision/recall results.

### 6.5 Reproducibility

[manifest.json](manifest.json) records actual execution time, dataset/artifact
SHA-256 hashes, model versions and installed package versions.
Source environments use Python 3.12.13, scikit-learn 1.8.0, XGBoost 3.4.1 and
SHAP 0.50.0; the manifest is authoritative for the extraction environment.
Raw and application-model artifacts remain unchanged by the research scripts.

## 7. Actual held-out results

All values below are proportions, not percentage units. Precision/recall/F1
refer to fraud/phishing as class 1. Accuracy, specificity and FNR were derived
from the original saved confusion counts, not guessed or recomputed on a
different dataset.

| Task / candidate | Accuracy | Precision | Recall | F1 | ROC-AUC | Average precision | Specificity | FPR | FNR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fraud / Logistic Regression | 0.999401 | 0.886076 | 0.736842 | 0.804598 | 0.964562 | 0.686510 | 0.999841 | 0.000159 | 0.263158 |
| Fraud / selected XGBoost | 0.999436 | 0.898734 | 0.747368 | 0.816092 | 0.967398 | 0.800049 | 0.999859 | 0.000141 | 0.252632 |
| Phishing / Logistic Regression | 0.995981 | 0.999022 | 0.996925 | 0.997972 | 0.996903 | 0.999975 | 0.878049 | 0.121951 | 0.003075 |
| Phishing / selected XGBoost | 0.996708 | 0.998195 | 0.998487 | 0.998341 | 0.998940 | 0.999991 | 0.774390 | 0.225610 | 0.001513 |

| Task / candidate | TN | FP | FN | TP |
|---|---:|---:|---:|---:|
| Fraud / Logistic Regression | 56,642 | 9 | 25 | 70 |
| Fraud / XGBoost | 56,643 | 8 | 24 | 71 |
| Phishing / Logistic Regression | 144 | 20 | 63 | 20,426 |
| Phishing / XGBoost | 127 | 37 | 31 | 20,458 |

Selected thresholds: fraud **0.9687055945396423**; phishing
**0.014913429506123066**. The baseline thresholds are preserved at full precision
in the model-results CSVs; fraud's baseline threshold is close to, but not equal
to, one. Never round it to one for actual prediction.

Average precision is scikit-learn `average_precision_score`, a weighted
precision-recall summary, not trapezoidal area under the exported PR coordinates.
The first ROC threshold is infinity; the last PR row has no decision threshold.
These are standard curve conventions, not missing predictions.

### Interpretation

- Fraud detects 71/95 labelled fraudulent test rows, misses 24, and falsely
  flags eight legitimate test rows. A 99.94% accuracy does not erase the
  approximately 25.26% fraud miss rate.
- The selected fraud model improves test average precision over its linear
  baseline, but the experiment has not established future-period performance.
- Phishing detects 20,458/20,489 positive URLs, but flags 37/164 benign URLs.
  Its minority-class specificity is only 77.44%.
- The linear phishing baseline has fewer benign false alarms than selected
  XGBoost. Selection optimized validation AP, not benign specificity or costs.
  This is a material trade-off, not justification for post-hoc test tuning.
- With test prevalence 20,489/20,653, the phishing no-skill AP baseline is
  approximately 0.992059. An AP of 0.999991 should not be read as a balanced-data
  generalization guarantee.

## 8. Explainable AI

SHAP is implemented for both tasks. Both saved selected models are XGBoost, so
the actual explainer is `TreeExplainer` with `feature_perturbation="interventional"`
and `model_output="raw"`. `LinearExplainer` exists for a selected Logistic
Regression artifact but is not the explainer used by the current saved models.

The background consists of 100 original training rows sampled with seed 42,
then transformed using the saved scaler. Input feature values in exports are
unscaled; SHAP evaluates the transformed model input.

For these binary XGBoost models:

```text
base_log_odds + sum(feature_SHAP_values) = prediction_log_odds
sigmoid(prediction_log_odds) ~= model.predict_proba(input)[class_1]
```

Positive contributions increase the classifier's class-1 log-odds relative to
that background. They are not percentages, causal effects, or explanations of
the original hidden variables behind a PCA component.

### Global and beeswarm evidence

The new research extraction explains a **stratified 512-row held-out sample per
task**, not all rows and not a balanced resample:

- Fraud: 511 legitimate, one fraud.
- Phishing: 508 phishing, four benign.

Mean absolute SHAP rankings therefore primarily describe majority-class model
behavior. They are not fraud-only or benign-only global importance estimates.
The stored CSVs permit alternative visualizations; a separate larger or
class-conditioned study should be labelled as a different explanation sample.

Highest sampled global features:

| Task | Leading mean-absolute-SHAP features |
|---|---|
| Fraud | V4, V14, V8, V15, V3, V12, V6 |
| Phishing | url_length, path_length, url_entropy, dot_count, domain_length, https, hyphen_count |

XGBoost's normalized gain ranks are exported separately. The rankings need not
agree with SHAP: gain describes fitted split utility, whereas sampled SHAP
describes contribution magnitudes on the specified explanation population.

### Actual individual transaction examples

Cases are the first test row of each observed outcome, selected retrospectively
to demonstrate true/false positives/negatives. They are not random examples.
Complete contributions for all 30 inputs are in `shap_analysis/fraud_examples.csv`.

| Case / cleaned index | Ground truth | Fraud probability | Decision | Largest contributions, log-odds |
|---|---|---:|---|---|
| TP / 115676 | Fraud | 0.9996647835 | Flagged | V14 +4.938198; V12 +2.228504; V4 +2.169458 |
| FP / 10578 | Legitimate | 0.9972280860 | Flagged | V14 +4.266301; V4 +2.309108; V12 +2.042625 |
| FN / 239334 | Fraud | 0.0306415465 | Not flagged | V4 +2.091906; V14 +1.677930; V11 -1.100466 |
| TN / 86249 | Legitimate | 0.0004119845 | Not flagged | V25 -0.641331; V4 +0.506135; V18 -0.463876 |

The false-positive example demonstrates that an apparently strong, additive
explanation does not establish a correct prediction. Fraud base log-odds in
these cases is approximately -7.351395.

Phishing case files and plots likewise cover TP/FP/FN/TN. One actual benign
false positive has estimated phishing probability 0.0188221242, above the very
low learned cutoff 0.0149134295. This illustrates why prediction class and
probability magnitude must be presented together.

Numerical probability reconstruction errors are recorded in SHAP metadata:
below 1.4e-7 for these extracted samples, substantially inside the checked 1e-5
tolerance.

## 9. Architecture and implementation

See [architecture.md](architecture.md) for all six requested Mermaid diagrams,
and [implementation_audit.md](implementation_audit.md) for code-backed component
status and exact technical stack. The actual communication path is:

```text
Browser -> Next.js /backend proxy -> FastAPI
FastAPI -> validated local ML pipeline -> SHAP
FastAPI <-> PostgreSQL investigation/result storage
FastAPI -> ReportLab PDF -> browser download
FastAPI -> optional fixed threat-provider APIs (only if configured)
```

Provider availability must be interpreted from actual status, not from adapter
existence. The verified local configuration has VirusTotal and Google Web Risk
not configured, and RDAP disabled. The analysis performs no provider calls.

## 10. Scientific audit and limitations

1. **Hostname overlap:** 13,840/20,653 phishing test rows share an exact hostname
   with training rows; 3,749 hostnames occur in both. This is roughly 67.01% of
   test URLs. Exact URL deduplication is not domain-disjoint evaluation.
2. **Temporal overlap:** all fraud partitions cover almost the same two-day
   time interval. No forward-looking chronological holdout was performed.
3. **Coverage selection:** 56,678 phishing source rows were filtered, mainly
   nonstandard ports. Results apply only to accepted standard-port inputs.
4. **Minority support:** only 95 fraudulent transaction and 164 benign URL test
   samples support important error-rate estimates. No confidence intervals were
   computed in the original experiments.
5. **Threshold objective:** maximum positive-class F1 can produce poor benign
   specificity when positives dominate. Cost-sensitive thresholds must be
   designed and validated prospectively, not optimized on this test set.
6. **No calibration:** classifier score estimates and very extreme thresholds
   are not empirically calibrated probabilities.
7. **Artifact retention gap:** only winning estimators were saved. Exact losing
   baseline ROC/PR curves, coefficients and SHAP outputs are unavailable without
   a clearly labelled reconstructed fit. This pack does not fabricate them.
8. **Training provenance gap:** original versions record Python/scikit-learn,
   but not every package, code commit or split index. This audit adds current
   versions/hashes and reconstructable split assignments without modifying the
   source artifacts.
9. **Feature semantics:** subdomain parsing is a heuristic, not public-suffix
   resolution; source token details are unavailable; ULB PCA meaning is hidden.
10. **Metric naming:** `fraud_detection_rate` is also present in phishing output;
    numerically it is positive-class recall, not financial-fraud evidence.
11. **Risk-bucket asymmetry:** fraud's learned threshold is above 0.8, so any
    flagged fraud row is high risk; its medium bucket is unreachable with the
    present `_risk` rule. This is an actual UX consequence, not a third class.
12. **No outcome guarantees:** provider absence, low scores, or an additive
    SHAP explanation cannot establish safety.

These are evidence/protocol limitations, not permission to change the deployed
model or retune against inspected test results during documentation.

## 11. Missing experiments and exact opt-in commands

Default extraction and graph generation do not retrain anything:

```bash
uv pip install --python backend/.venv/bin/python -r reports/ml_analysis/requirements.txt
PYTHONPATH=backend backend/.venv/bin/python reports/ml_analysis/analyze.py
backend/.venv/bin/python reports/ml_analysis/write_summaries.py
backend/.venv/bin/python reports/ml_analysis/graph_generation.py
```

Two explicitly new, optional experiments are supplied but **not executed**:

```bash
# Required only to reconstruct unsaved Logistic Regression curve/coefficient data.
# Fits only the missing baselines and checks original validation/test metrics.
PYTHONPATH=backend backend/.venv/bin/python \
  reports/ml_analysis/missing_experiments.py recover-baselines

# New 3-fold training-only learning curves, five sample sizes; no test tuning.
# These are not original learning histories and may take substantially longer.
PYTHONPATH=backend backend/.venv/bin/python \
  reports/ml_analysis/missing_experiments.py learning-curves
```

Outputs are explicitly labelled under `new_experiments/`; application artifacts
are not overwritten. If a baseline reconstruction fails metric agreement, stop
and investigate package/data drift rather than presenting it as the original.

Not implemented as completed experiments: domain-disjoint/temporal holdouts,
calibration, ablation studies, external validation, fairness analysis, anomaly
benchmarking, uncertainty intervals, or provider efficacy benchmarking.
These require new protocols/data and cannot be recovered from aggregate scores.

## 12. Future scope

- Prespecify domain-grouped phishing and chronological fraud evaluation.
- Expand representative benign URL coverage; validate filtering effects.
- Select thresholds using validation-only investigation costs or constrained
  false-positive targets, followed by a genuinely untouched future holdout.
- Assess calibration and uncertainty.
- Persist every candidate, split IDs, configurations, package versions and score
  vectors at training time.
- Evaluate larger/class-conditioned SHAP samples and stability.
- Assess Isolation Forest separately with an appropriate anomaly protocol.
- Before public deployment, add authentication, retention/deletion controls,
  rate limits, job processing and operational monitoring.

These are planned improvements, not features or experiments already completed.

## 13. Conclusion and strongest presentation findings

ExplainPay demonstrates an implemented raw-data-to-investigation workflow with
reproducible selected-model results, genuine SHAP explanations and saved reports.
Its strongest scientific finding is not merely a high score: a very high phishing
F1 coexists with a material benign false-alarm rate under an imbalanced,
domain-overlapping evaluation. The system can explain a decision without proving
it correct. That distinction, along with explicit PCA/privacy limitations,
supports a more credible presentation than unqualified dashboard accuracy.

## References and evidence

- ULB source: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
- Phishing source and encoding: https://www.kaggle.com/datasets/victusadi/phishing-urls-dataset-with-extracted-features
- scikit-learn metrics: https://scikit-learn.org/stable/modules/model_evaluation.html
- Stratified splitting: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html
- XGBoost parameters: https://xgboost.readthedocs.io/en/stable/parameter.html
- SHAP TreeExplainer: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html
- SHAP LinearExplainer: https://shap.readthedocs.io/en/latest/generated/shap.LinearExplainer.html
- Isolation Forest: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
- Local methodology: `backend/app/ml/train.py`, `runtime.py`, `urls.py`.
- Local artifacts: ignored `data/models/{fraud,phishing}.joblib` and metrics JSON.
- Reproduced evidence: [manifest.json](manifest.json), [graph_data/](graph_data/),
  [shap_analysis/](shap_analysis/), [dataset_summary.md](dataset_summary.md).

Library reference URLs identify methodology documentation; this pack does not
claim an exhaustive literature review or independent replication of external
published research.
