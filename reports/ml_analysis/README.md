# ExplainPay ML research pack

Start with [technical_content.md](technical_content.md) for the research narrative,
[dataset_summary.md](dataset_summary.md) for every schema/statistic/feature
definition, and [architecture.md](architecture.md) for six Mermaid diagrams.
[implementation_audit.md](implementation_audit.md) distinguishes actual features,
technical limitations, and planned work.

## Reproduce the pack

From the repository root, with the original datasets and trusted model artifacts
already present:

```bash
uv pip install --python backend/.venv/bin/python -r reports/ml_analysis/requirements.lock
PYTHONPATH=backend backend/.venv/bin/python reports/ml_analysis/analyze.py
backend/.venv/bin/python reports/ml_analysis/write_summaries.py
backend/.venv/bin/python reports/ml_analysis/graph_generation.py
backend/.venv/bin/python -m pytest reports/ml_analysis/test_analysis.py -q
```

These commands do not train models, modify the application, visit submitted
URLs, or call external providers. Extraction refuses mismatched input hashes,
cleaning records, splits, scaler means, SHAP backgrounds or saved metrics.

Optional **new** experiments are available but not part of the original results:

```bash
PYTHONPATH=backend backend/.venv/bin/python reports/ml_analysis/missing_experiments.py recover-baselines
PYTHONPATH=backend backend/.venv/bin/python reports/ml_analysis/missing_experiments.py learning-curves
```

The first reconstructs only unsaved Logistic Regression estimators and verifies
aggregate agreement. The second runs a new three-fold, training-only AP learning
curve with fixed selected-model hyperparameters. Neither overwrites deployed
artifacts or tunes on test data. These commands were syntax-checked, not executed.

## Assets

| Asset | Interpretation |
|---|---|
| `*_model_results.csv` | Every supervised candidate's saved validation/test results; derived accuracy/specificity/FNR |
| `*_confusion_matrix.csv` | TN, FP, FN, TP for both candidates and both evaluation splits |
| `*_roc_data.csv`, `*_pr_data.csv` | Exact held-out score curves from each selected saved model |
| `*_feature_importance.csv` | Sampled mean-absolute SHAP, signed SHAP mean, and normalized XGBoost gain |
| `graph_data/` | Full numeric statistics, class comparisons, histograms, correlations, missingness and audit evidence |
| `shap_analysis/` | Reproducible sample values, additive explanations and actual TP/FP/FN/TN cases |
| `figures/` | 300-DPI PNGs and captions generated from these data |
| `manifest.json` | Data/artifact hashes, runtime versions and extraction provenance |
| `requirements.lock` | Exact analysis/plotting environment |

Curves are not invented for unsaved baseline estimators. Original learning curves
and anomaly evaluation were not recorded. See the final audit and technical
content for missing experiments and their implications.

## Sharing and scientific integrity

- Raw datasets, artifacts, URLs and credentials are not copied into this pack.
- Row-level split indices, predictions and SHAP feature values are local,
  Git-ignored exports; aggregate CSVs/figures and narrative files are shareable.
- Do not publicly share row-level research exports without reviewing dataset
  licensing and data-protection requirements.
- A cleaned row index is not an original customer/merchant/transaction ID.
- The 512-row SHAP samples preserve the dataset's extreme imbalance; they do not
  constitute balanced or full-population importance estimates.
- Phishing F1/AP are very high, but 22.56% of benign test URLs were flagged and
  67.01% of test rows share a training hostname. These limitations belong beside
  the performance numbers in any presentation.
- No slides or presentation PDFs were created.
