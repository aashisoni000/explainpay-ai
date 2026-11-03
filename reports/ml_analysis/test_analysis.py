"""Verify exported research assets against their recorded evidence."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent


@pytest.mark.parametrize("kind", ["fraud", "phishing"])
def test_counts_statistics_and_splits(kind: str) -> None:
    audit = json.loads((HERE / "graph_data" / f"{kind}_audit.json").read_text())
    assignments = pd.read_csv(HERE / "graph_data" / f"{kind}_split_assignments.csv")
    assert assignments.cleaned_row_index.is_unique
    assert len(assignments) == audit["cleaned_rows"]
    for split, expected in audit["splits"].items():
        subset = assignments[assignments.split == split]
        assert len(subset) == expected["size"]
        assert {str(key): int(value) for key, value in subset.target.value_counts().items()} == expected["class_distribution"]
    stats = pd.read_csv(HERE / "graph_data" / f"{kind}_cleaned_statistics.csv")
    assert set(stats.feature) == set(audit["input_features"])
    assert stats["count"].eq(audit["cleaned_rows"]).all()
    hist = pd.read_csv(HERE / "graph_data" / f"{kind}_histograms.csv")
    for (population, _, label), group in hist.groupby(["population", "feature", "class_label"]):
        counts = audit["raw_class_distribution"] if population == "raw" else audit["cleaned_class_distribution"]
        assert group["count"].sum() == counts[str(label)]


@pytest.mark.parametrize("kind", ["fraud", "phishing"])
def test_metrics_curves_and_confusion(kind: str) -> None:
    results = pd.read_csv(HERE / f"{kind}_model_results.csv")
    assert len(results) == 4
    for row in results.itertuples():
        assert row.support == row.tn + row.fp + row.fn + row.tp
        assert row.accuracy == pytest.approx((row.tn + row.tp) / row.support)
        assert row.specificity + row.false_positive_rate == pytest.approx(1)
        assert row.recall + row.false_negative_rate == pytest.approx(1)
        assert 0 <= row.threshold <= 1
    roc = pd.read_csv(HERE / f"{kind}_roc_data.csv")
    pr = pd.read_csv(HERE / f"{kind}_pr_data.csv")
    assert roc.model.unique().tolist() == ["xgboost"]
    assert pr.model.unique().tolist() == ["xgboost"]
    assert roc.fpr.is_monotonic_increasing and roc.tpr.is_monotonic_increasing
    assert pr.recall.is_monotonic_decreasing
    assert np.isinf(roc.threshold.iloc[0])
    assert pd.isna(pr.threshold.iloc[-1])


@pytest.mark.parametrize("kind", ["fraud", "phishing"])
def test_shap_reconstruction_and_importance(kind: str) -> None:
    shap = pd.read_csv(HERE / "shap_analysis" / f"{kind}_values.csv")
    importance = pd.read_csv(HERE / f"{kind}_feature_importance.csv").set_index("feature")
    means = shap.assign(absolute=shap.shap_value.abs()).groupby("feature").absolute.mean()
    assert np.allclose(importance.loc[means.index, "mean_abs_shap"], means)
    sample = shap.groupby("sample_id").agg(shap_sum=("shap_value", "sum"), base=("base_value", "first"), probability=("probability", "first"))
    assert len(sample) == 512
    assert np.allclose(1 / (1 + np.exp(-(sample.base + sample.shap_sum))), sample.probability, atol=1e-5)
    examples = pd.read_csv(HERE / "shap_analysis" / f"{kind}_examples.csv")
    assert set(examples.outcome) == {"TP", "FP", "FN", "TN"}
    for _, case in examples.groupby("case_id"):
        assert 1 / (1 + np.exp(-(case.base_value.iloc[0] + case.shap_value.sum()))) == pytest.approx(case.probability.iloc[0], abs=1e-5)


def test_artifacts_not_retrained() -> None:
    manifest = json.loads((HERE / "manifest.json").read_text())
    assert manifest["retrained_models"] is False
    assert manifest["seed"] == 42
    root = HERE.parents[1]
    for kind, evidence in manifest["datasets"].items():
        with (root / "data/models" / f"{kind}.joblib").open("rb") as handle:
            assert hashlib.file_digest(handle, "sha256").hexdigest() == evidence["artifact_sha256"]
