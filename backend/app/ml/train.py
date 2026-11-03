"""Inspect datasets, train real models, and persist auditable evaluations."""

import argparse
import csv
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from .runtime import ROOT, TRANSACTION_FEATURES, model_directory
from .urls import FEATURE_VERSION, extract_features, normalize_url

SEED = 42


def read_dataset(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise ValueError(f"Dataset not found: {path}. Download the real Kaggle dataset; no model was trained.")
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            header = next(csv.reader(source), [])
        if not header or any(not name.strip() for name in header) or len(header) != len(set(header)):
            raise ValueError("CSV headers must be nonempty and unique.")
        frame = pd.read_csv(path, low_memory=False)
    except (csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError) as error:
        raise ValueError(f"Cannot read dataset: {error}") from error
    if frame.empty or frame.columns.duplicated().any():
        raise ValueError("Dataset must be nonempty and have unique column names.")
    return frame


def inspect_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    candidates = {}
    for column in frame.columns:
        unique = frame[column].dropna().unique()
        if len(unique) <= 10:
            candidates[str(column)] = [str(value) for value in unique]
    return {
        "rows": len(frame),
        "columns": list(frame.columns),
        "missing_values": {str(column): int(count) for column, count in frame.isna().sum().items() if count},
        "duplicate_rows": int(frame.duplicated().sum()),
        "possible_label_values": candidates,
        "sample_types": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
    }


def prepare_fraud(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict[str, Any]]:
    required = TRANSACTION_FEATURES + ["Class"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    data = frame[required].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(data.to_numpy(dtype=float)).all():
        raise ValueError("Transaction dataset contains missing or nonfinite values.")
    if not set(data["Class"].unique()) <= {0, 1} or data["Class"].nunique() != 2:
        raise ValueError("Class must contain both binary labels 0 and 1.")
    if (data[["Time", "Amount"]] < 0).any().any():
        raise ValueError("Time and Amount cannot be negative.")
    if data.groupby(TRANSACTION_FEATURES, dropna=False)["Class"].nunique().gt(1).any():
        raise ValueError("Identical transaction features have conflicting labels.")
    before = len(data)
    data = data.drop_duplicates(subset=TRANSACTION_FEATURES).reset_index(drop=True)
    return data[TRANSACTION_FEATURES].astype(float), data["Class"].astype(int), {
        "duplicates_removed": before - len(data),
        "label_mapping": {"0": "legitimate", "1": "fraud"},
        "features": "V1-V28 are anonymized PCA components; original merchant identity is unavailable.",
    }


def prepare_phishing(
    frame: pd.DataFrame,
    url_column: str,
    target_column: str,
    positive_label: str,
    negative_label: str,
) -> tuple[pd.DataFrame, pd.Series, dict[str, Any]]:
    if url_column not in frame or target_column not in frame or url_column == target_column:
        raise ValueError("Select distinct URL and label columns from the inspected schema.")
    if positive_label == negative_label:
        raise ValueError("Positive and negative label values must differ.")
    if frame[[url_column, target_column]].isna().any().any():
        raise ValueError("URL or target values are missing. Review and clean the source explicitly.")
    labels = frame[target_column].astype(str).str.strip()
    if set(labels.unique()) != {positive_label, negative_label}:
        raise ValueError(f"Observed labels {sorted(labels.unique())} do not match the explicit label mapping.")
    valid_urls: list[str] = []
    valid_labels: list[int] = []
    rejected = 0
    for value, label in zip(frame[url_column], labels, strict=True):
        try:
            normalized = normalize_url(str(value).strip())
        except ValueError:
            rejected += 1
            continue
        valid_urls.append(normalized)
        valid_labels.append(int(label == positive_label))
    data = pd.DataFrame({"url": valid_urls, "label": valid_labels})
    if data.empty:
        raise ValueError("No valid public HTTP/HTTPS URLs remain after validation.")
    if data.groupby("url")["label"].nunique().gt(1).any():
        raise ValueError("Duplicate normalized URLs contain conflicting labels; resolve them before training.")
    before = len(data)
    data = data.drop_duplicates("url").reset_index(drop=True)
    features = pd.DataFrame([extract_features(url) for url in data["url"]], dtype=float)
    return features, data["label"].astype(int), {
        "url_column": url_column,
        "target_column": target_column,
        "label_mapping": {positive_label: "phishing", negative_label: "legitimate"},
        "invalid_urls_removed": rejected,
        "duplicate_urls_removed": before - len(data),
        "features": "Only deterministic URL lexical features; supplied extracted features are not trusted.",
    }


def choose_threshold(labels: pd.Series, probabilities: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    scores = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    if not len(thresholds):
        raise ValueError("Validation scores have no usable decision threshold.")
    return float(thresholds[int(np.argmax(scores))])


def evaluate(labels: pd.Series, probabilities: np.ndarray, threshold: float) -> dict[str, Any]:
    predictions = probabilities >= threshold
    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    tn, fp, fn, tp = [int(value) for value in matrix.ravel()]
    return {
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "pr_auc": float(average_precision_score(labels, probabilities)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "false_positive_rate": fp / (tn + fp) if tn + fp else 0,
        "fraud_detection_rate": tp / (tp + fn) if tp + fn else 0,
        "threshold": threshold,
    }


def fit_models(features: pd.DataFrame, labels: pd.Series, kind: str) -> dict[str, Any]:
    if labels.nunique() != 2 or labels.value_counts().min() < 10:
        raise ValueError("At least ten unique rows of each class are required for stratified training/validation/test splits.")
    train_validation, test, y_train_validation, y_test = train_test_split(
        features, labels, test_size=0.2, stratify=labels, random_state=SEED,
    )
    train, validation, y_train, y_validation = train_test_split(
        train_validation, y_train_validation, test_size=0.25, stratify=y_train_validation, random_state=SEED,
    )
    weight = float((y_train == 0).sum() / (y_train == 1).sum())
    classifiers = {
        "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED),
        "xgboost": XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.06,
            subsample=0.9, colsample_bytree=0.9, scale_pos_weight=weight,
            eval_metric="logloss", tree_method="hist", n_jobs=2, random_state=SEED,
        ),
    }
    candidates: dict[str, Pipeline] = {}
    validation_scores: dict[str, dict[str, Any]] = {}
    for name, classifier in classifiers.items():
        pipeline = Pipeline([("scale", StandardScaler()), ("model", classifier)])
        pipeline.fit(train, y_train)
        scores = pipeline.predict_proba(validation)[:, 1]
        threshold = choose_threshold(y_validation, scores)
        candidates[name] = pipeline
        validation_scores[name] = evaluate(y_validation, scores, threshold)
    selected = max(validation_scores, key=lambda name: validation_scores[name]["pr_auc"])
    pipeline = candidates[selected]
    threshold = validation_scores[selected]["threshold"]
    # Test data is evaluated only after model and threshold selection are locked.
    test_scores = {
        name: evaluate(y_test, candidate.predict_proba(test)[:, 1], validation_scores[name]["threshold"])
        for name, candidate in candidates.items()
    }
    anomaly = None
    if kind == "fraud":
        anomaly = IsolationForest(
            n_estimators=100, contamination=0.01, max_samples=min(4096, int((y_train == 0).sum())),
            random_state=SEED, n_jobs=2,
        ).fit(train.loc[y_train == 0])
    report = {
        "selected_model": selected,
        "threshold": threshold,
        "threshold_selection": "Maximum validation F1; model selected by validation average precision (PR-AUC).",
        "validation": validation_scores,
        "test": test_scores[selected],
        "test_comparison": test_scores,
        "split": {"train": len(train), "validation": len(validation), "test": len(test), "seed": SEED},
        "class_distribution": {str(label): int(count) for label, count in labels.value_counts().items()},
        "scale_pos_weight": weight,
        "explanation_units": "SHAP contributions are log-odds, not probability percentage points.",
        "limitations": [
            "Research dataset evaluation is not a guarantee of real-world performance.",
            "Random stratified splits do not measure temporal or domain-level distribution shift.",
            "Risk levels are triage labels, not proof; high means flagged and probability at least 0.8.",
            "Anomaly detection is separate from supervised fraud classification.",
        ],
    }
    return {
        "pipeline": pipeline,
        "features": list(features.columns),
        "threshold": threshold,
        "background": train.sample(min(100, len(train)), random_state=SEED),
        "metrics": report,
        "anomaly": anomaly,
        "model_name": selected,
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.path) if args.path else ROOT / "data/raw" / ("transactions/creditcard.csv" if args.kind == "fraud" else "websites/phishing_urls.csv")
    frame = read_dataset(path)
    inspection = inspect_dataset(frame)
    if args.inspect:
        return inspection
    if args.kind == "fraud":
        features, labels, preparation = prepare_fraud(frame)
    else:
        if any(value is None for value in (args.url_column, args.target_column, args.positive_label, args.negative_label)):
            raise ValueError("Inspect the phishing schema first, then provide --url-column, --target-column, --positive-label, and --negative-label.")
        features, labels, preparation = prepare_phishing(
            frame, args.url_column, args.target_column, args.positive_label, args.negative_label,
        )
    artifact = fit_models(features, labels, args.kind)
    created = datetime.now(UTC).isoformat()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    artifact.update({
        "kind": args.kind,
        "feature_version": "ulb-v1" if args.kind == "fraud" else FEATURE_VERSION,
        "version": f"{args.kind}-{created}",
    })
    artifact["metrics"].update({
        "created_at": created,
        "dataset_sha256": digest.hexdigest(),
        "inspection": inspection,
        "preparation": preparation,
        "versions": {"python": platform.python_version(), "sklearn": sklearn.__version__},
    })
    output = Path(args.output) if args.output else model_directory()
    output.mkdir(parents=True, exist_ok=True)
    pending = output / f".{args.kind}.joblib.tmp"
    joblib.dump(artifact, pending)
    # Check persisted inference and SHAP before publishing this artifact.
    restored = joblib.load(pending)
    restored["pipeline"].predict_proba(features.iloc[:1])
    from .runtime import build_explainer, explain_artifact
    explain_artifact(restored, features.iloc[:1], build_explainer(restored))
    pending.replace(output / f"{args.kind}.joblib")
    (output / f"{args.kind}.metrics.json").write_text(json.dumps(artifact["metrics"], indent=2), encoding="utf-8")
    return artifact["metrics"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["fraud", "phishing"])
    parser.add_argument("--path")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--url-column")
    parser.add_argument("--target-column")
    parser.add_argument("--positive-label")
    parser.add_argument("--negative-label")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = train(args)
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
