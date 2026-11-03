"""Synthetic unit fixtures test mechanics, not real-world model performance."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from app.ml import runtime
from app.ml.runtime import TRANSACTION_FEATURES, ModelUnavailable, validate_transaction
from app.ml.train import (
    choose_threshold,
    fit_models,
    prepare_fraud,
    prepare_phishing,
    read_dataset,
    train,
)
from app.ml.urls import extract_features, normalize_url


@pytest.mark.parametrize("url", [
    "http://127.0.0.1", "http://169.254.169.254/latest/meta-data",
    "http://[::1]", "http://localhost", "file:///etc/passwd",
    "https://user:password@example.com", "https://example.com:8080",
    "http://2130706433", "http://0x7f000001", "https://example.com\\@localhost",
    "https://example.com\n", "http://internal.local", "https://%31%32%37.0.0.1",
])
def test_url_rejects_unsafe_inputs(url: str) -> None:
    with pytest.raises(ValueError):
        normalize_url(url)


def test_url_normalization_and_feature_consistency() -> None:
    normalized = normalize_url("EXAMPLE.COM/login?verify=1#fragment")
    assert normalized == "https://example.com/login?verify=1"
    assert extract_features(normalized) == extract_features("EXAMPLE.COM/login?verify=1#fragment")
    assert extract_features(normalized)["https"] == 1
    assert extract_features(normalized)["parameter_count"] == 1
    assert len(extract_features(normalized)) == 15


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "bad", None])
def test_transaction_finite_validation(value: object) -> None:
    row: dict[str, object] = dict.fromkeys(TRANSACTION_FEATURES, 0)
    row["V2"] = value
    with pytest.raises(ValueError):
        validate_transaction(row)


def test_transaction_missing_and_negative() -> None:
    with pytest.raises(ValueError, match="Missing"):
        validate_transaction({})
    row = dict.fromkeys(TRANSACTION_FEATURES, 0)
    row["Amount"] = -1
    with pytest.raises(ValueError, match="negative"):
        validate_transaction(row)


def test_datasets_missing_are_explicit(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Dataset not found"):
        read_dataset(tmp_path / "missing.csv")


def test_duplicate_csv_headers_are_not_silently_renamed(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.csv"
    path.write_text("url,url,label\nexample.com,example.com,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        read_dataset(path)


def test_missing_model_has_no_predictions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    runtime.load_model.cache_clear()
    with pytest.raises(ModelUnavailable, match="Train it"):
        runtime.predict_transaction(dict.fromkeys(TRANSACTION_FEATURES, 0))
    assert runtime.model_status()["fraud"]["available"] is False
    runtime.load_model.cache_clear()


def test_corrupt_model_is_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    (tmp_path / "fraud.joblib").write_bytes(b"not-a-valid-trained-model")
    runtime.load_model.cache_clear()
    with pytest.raises(ModelUnavailable, match="Cannot load"):
        runtime.load_model("fraud")
    runtime.load_model.cache_clear()


def test_fraud_deduplicates_before_split() -> None:
    frame = pd.DataFrame([dict.fromkeys(TRANSACTION_FEATURES, 0), dict.fromkeys(TRANSACTION_FEATURES, 1)])
    frame["Class"] = [0, 1]
    duplicate = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
    x, y, info = prepare_fraud(duplicate)
    assert len(x) == len(y) == 2
    assert info["duplicates_removed"] == 1
    conflicting = pd.concat([frame, frame.iloc[:1].assign(Class=1)], ignore_index=True)
    with pytest.raises(ValueError, match="conflicting"):
        prepare_fraud(conflicting)


def test_phishing_requires_explicit_labels_and_detects_conflicts() -> None:
    frame = pd.DataFrame({"address": ["example.com", "https://example.com/"], "target": ["bad", "good"]})
    with pytest.raises(ValueError, match="conflicting"):
        prepare_phishing(frame, "address", "target", "bad", "good")
    with pytest.raises(ValueError, match="Observed labels"):
        prepare_phishing(frame, "address", "target", "1", "0")


def test_threshold_uses_validation_labels() -> None:
    threshold = choose_threshold(pd.Series([0, 0, 1, 1]), np.array([0.1, 0.2, 0.4, 0.8]))
    assert threshold == 0.4
    assert choose_threshold(pd.Series([0, 0, 1, 1]), np.array([0.1, 0.4, 1, 1])) == 1


def test_real_training_artifact_roundtrip_on_labelled_synthetic_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(rng.normal(size=(80, 30)), columns=TRANSACTION_FEATURES)
    frame["Time"] = np.arange(80)
    frame["Amount"] = np.abs(frame["Amount"])
    frame["Class"] = np.tile([0, 1], 40)
    path = tmp_path / "SYNTHETIC_TEST_ONLY.csv"
    frame.to_csv(path, index=False)
    args = argparse.Namespace(kind="fraud", path=str(path), inspect=False, output=str(tmp_path), url_column=None, target_column=None, positive_label=None, negative_label=None)
    report = train(args)
    assert sum(report["split"][key] for key in ("train", "validation", "test")) == 80
    assert report["test"]["confusion_matrix"]
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    runtime.load_model.cache_clear()
    runtime._explainer.cache_clear()
    result = runtime.predict_transaction(frame.iloc[0].to_dict())
    assert 0 <= result["fraud_probability"] <= 1
    assert len(result["explanation"]) == 30
    log_odds = result["base_value"] + sum(item["contribution"] for item in result["explanation"])
    probability_from_shap = 1 / (1 + np.exp(-log_odds))
    assert probability_from_shap == pytest.approx(result["fraud_probability"], abs=1e-5)
    assert result["merchant_url"] is None
    assert result["is_anomaly"] in {True, False}
    runtime.load_model.cache_clear()
    runtime._explainer.cache_clear()


def test_small_training_is_rejected() -> None:
    with pytest.raises(ValueError, match="ten unique"):
        fit_models(pd.DataFrame({"x": [1, 2]}), pd.Series([0, 1]), "phishing")


def test_phishing_real_pipeline_and_explanations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = []
    for index in range(40):
        rows.append({"address": f"https://store-{index}.com/catalog", "target": "legitimate"})
        rows.append({"address": f"http://verify-login-{index}.com/account?password={index}", "target": "phishing"})
    path = tmp_path / "SYNTHETIC_TEST_ONLY.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    train(argparse.Namespace(
        kind="phishing", path=str(path), inspect=False, output=str(tmp_path),
        url_column="address", target_column="target", positive_label="phishing", negative_label="legitimate",
    ))
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    runtime.load_model.cache_clear()
    runtime._explainer.cache_clear()
    result = runtime.predict_website("https://store-999.com/catalog")
    assert 0 <= result["ml_probability"] <= 1
    assert len(result["explanation"]) == 15
    assert list(result["features"]) == runtime.load_model("phishing")["features"]
    runtime.load_model.cache_clear()
    runtime._explainer.cache_clear()


@pytest.mark.parametrize("model_name", ["logistic_regression", "xgboost"])
def test_both_model_explainers_are_additive(model_name: str) -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from xgboost import XGBClassifier

    frame = pd.DataFrame({"x": np.arange(60), "y": np.sin(np.arange(60))})
    labels = pd.Series([0] * 30 + [1] * 30)
    model = LogisticRegression() if model_name == "logistic_regression" else XGBClassifier(n_estimators=10, n_jobs=1)
    pipeline = Pipeline([("scale", StandardScaler()), ("model", model)]).fit(frame, labels)
    artifact = {"pipeline": pipeline, "background": frame, "model_name": model_name, "features": list(frame.columns)}
    explanation, base = runtime.explain_artifact(artifact, frame.iloc[:1], runtime.build_explainer(artifact))
    log_odds = base + sum(float(item["contribution"]) for item in explanation)
    assert 1 / (1 + np.exp(-log_odds)) == pytest.approx(pipeline.predict_proba(frame.iloc[:1])[0, 1], abs=1e-5)
