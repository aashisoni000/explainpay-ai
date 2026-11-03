"""Load only locally trained artifacts; never synthesize predictions."""

import math
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap
from dotenv import dotenv_values
from sklearn.pipeline import Pipeline

from .urls import FEATURE_VERSION, extract_features, normalize_url

ROOT = Path(__file__).resolve().parents[3]
TRANSACTION_FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]


class ModelUnavailable(RuntimeError):
    """A trusted, compatible trained artifact is required."""


def model_directory() -> Path:
    configured = os.getenv("MODEL_DIR") or dotenv_values(ROOT / ".env").get("MODEL_DIR") or "data/models"
    path = Path(configured)
    return path if path.is_absolute() else ROOT / path


@lru_cache(maxsize=2)
def load_model(kind: str) -> dict[str, Any]:
    if kind not in {"fraud", "phishing"}:
        raise ValueError("Unknown model kind.")
    path = model_directory() / f"{kind}.joblib"
    if not path.is_file():
        raise ModelUnavailable(f"{kind.capitalize()} model unavailable. Train it with: python -m app.ml.train {kind}")
    try:
        artifact = joblib.load(path)
        required = {"pipeline", "features", "threshold", "background", "metrics", "version", "kind", "feature_version", "model_name"}
        if not isinstance(artifact, dict) or not required.issubset(artifact):
            raise ValueError("Incomplete artifact schema.")
        if artifact["kind"] != kind:
            raise ValueError("Artifact task mismatch.")
        if not isinstance(artifact["pipeline"], Pipeline) or artifact["model_name"] not in {"logistic_regression", "xgboost"}:
            raise ValueError("Unsupported trained model pipeline.")
        expected = TRANSACTION_FEATURES if kind == "fraud" else list(extract_features("https://example.com"))
        version = "ulb-v1" if kind == "fraud" else FEATURE_VERSION
        if artifact["features"] != expected or artifact["feature_version"] != version:
            raise ValueError("Feature schema mismatch; retrain the model.")
        if not 0 <= float(artifact["threshold"]) <= 1:
            raise ValueError("Invalid prediction threshold.")
        return artifact
    except (OSError, ValueError, TypeError, KeyError, ImportError, EOFError, pickle.UnpicklingError) as error:
        raise ModelUnavailable(f"Cannot load {kind} model: {error}") from error


def model_status() -> dict[str, dict[str, Any]]:
    status: dict[str, dict[str, Any]] = {}
    for kind in ("fraud", "phishing"):
        try:
            model = load_model(kind)
            status[kind] = {"available": True, "error": None, "version": model["version"]}
        except ModelUnavailable as error:
            status[kind] = {"available": False, "error": str(error)}
    return status


def metrics(kind: str) -> dict[str, Any]:
    return load_model(kind)["metrics"]


def validate_transaction(row: dict[str, Any]) -> dict[str, float]:
    missing = set(TRANSACTION_FEATURES) - row.keys()
    if missing:
        raise ValueError("Missing transaction columns: " + ", ".join(sorted(missing)))
    validated: dict[str, float] = {}
    for feature in TRANSACTION_FEATURES:
        value = row[feature]
        if isinstance(value, bool):
            raise ValueError(f"{feature} must be a finite number.")  # noqa: TRY004 - API validation contract
        try:
            number = float(value)
        except (ValueError, TypeError) as error:
            raise ValueError(f"{feature} must be a finite number.") from error
        if not math.isfinite(number):
            raise ValueError(f"{feature} must be a finite number.")
        if feature in {"Amount", "Time"} and number < 0:
            raise ValueError(f"{feature} cannot be negative.")
        validated[feature] = number
    return validated


@lru_cache(maxsize=2)
def _explainer(kind: str) -> Any:
    return build_explainer(load_model(kind))


def build_explainer(artifact: dict[str, Any]) -> Any:
    pipeline = artifact["pipeline"]
    background = pipeline.named_steps["scale"].transform(artifact["background"])
    classifier = pipeline.named_steps["model"]
    if artifact["model_name"] == "logistic_regression":
        return shap.LinearExplainer(classifier, background)
    return shap.TreeExplainer(classifier, data=background, feature_perturbation="interventional", model_output="raw")


def explain(kind: str, frame: pd.DataFrame) -> tuple[list[dict[str, float | str]], float]:
    artifact = load_model(kind)
    return explain_artifact(artifact, frame, _explainer(kind))


def explain_artifact(
    artifact: dict[str, Any], frame: pd.DataFrame, explainer: Any,
) -> tuple[list[dict[str, float | str]], float]:
    transformed = artifact["pipeline"].named_steps["scale"].transform(frame)
    result = explainer(transformed, check_additivity=True) if artifact["model_name"] != "logistic_regression" else explainer(transformed)
    values = np.asarray(result.values)
    if values.ndim == 3:
        values = values[:, :, 1]
    base = np.asarray(result.base_values).reshape(-1)[0]
    contributions = [
        {"feature": feature, "value": float(frame.iloc[0][feature]), "contribution": float(values[0, index])}
        for index, feature in enumerate(artifact["features"])
    ]
    contributions.sort(key=lambda item: abs(float(item["contribution"])), reverse=True)
    return contributions, float(base)


def _risk(probability: float, threshold: float) -> str:
    if probability >= max(threshold, 0.8):
        return "high"
    return "medium" if probability >= threshold else "low"


def predict_transaction(row: dict[str, Any]) -> dict[str, Any]:
    validated = validate_transaction(row)
    merchant_url = normalize_url(row["merchant_url"]) if row.get("merchant_url") else None
    artifact = load_model("fraud")
    frame = pd.DataFrame([validated], columns=artifact["features"])
    probability = float(artifact["pipeline"].predict_proba(frame)[0, 1])
    contributions, base_value = explain("fraud", frame)
    anomaly = artifact.get("anomaly")
    anomaly_score = float(anomaly.decision_function(frame)[0]) if anomaly is not None else None
    return {
        "fraud_probability": probability,
        "prediction": int(probability >= artifact["threshold"]),
        "risk_level": _risk(probability, artifact["threshold"]),
        "threshold": artifact["threshold"],
        "explanation": contributions,
        "base_value": base_value,
        "anomaly_score": anomaly_score,
        "is_anomaly": bool(anomaly_score < 0) if anomaly_score is not None else None,
        "model_version": artifact["version"],
        "merchant_url": merchant_url,
    }


def predict_website(url: str) -> dict[str, Any]:
    from urllib.parse import urlsplit

    normalized = normalize_url(url)
    features = extract_features(normalized)
    artifact = load_model("phishing")
    frame = pd.DataFrame([features], columns=artifact["features"])
    probability = float(artifact["pipeline"].predict_proba(frame)[0, 1])
    contributions, base_value = explain("phishing", frame)
    return {
        "url": normalized,
        "normalized_domain": urlsplit(normalized).hostname,
        "ml_probability": probability,
        "ml_prediction": int(probability >= artifact["threshold"]),
        "risk_level": _risk(probability, artifact["threshold"]),
        "threshold": artifact["threshold"],
        "explanation": contributions,
        "base_value": base_value,
        "features": features,
        "model_version": artifact["version"],
    }
