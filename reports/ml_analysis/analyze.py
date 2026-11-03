"""Reproduce saved experiments and export local research data without retraining."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.runtime import build_explainer, load_model, model_directory
from app.ml.train import (
    SEED,
    evaluate,
    inspect_dataset,
    prepare_fraud,
    prepare_phishing,
    read_dataset,
)
from app.ml.urls import normalize_url

SOURCES = {
    "fraud": "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
    "phishing": "https://www.kaggle.com/datasets/victusadi/phishing-urls-dataset-with-extracted-features",
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_json(path: Path, value: Any) -> None:
    def safe(item: Any) -> Any:
        if isinstance(item, dict):
            return {key: safe(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [safe(child) for child in item]
        if isinstance(item, (float, np.floating)) and not np.isfinite(item):
            return str(item)
        return item
    path.write_text(json.dumps(safe(value), indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")


def csv(path: Path, value: Any, **kwargs: Any) -> None:
    pd.DataFrame(value).to_csv(path, index=False, **kwargs)


def statistics(frame: pd.DataFrame, labels: pd.Series | None = None) -> pd.DataFrame:
    rows = []
    numeric = frame.select_dtypes(include="number")
    groups = [(None, numeric)] if labels is None else [(label, numeric.loc[labels == label]) for label in sorted(labels.unique())]
    for label, group in groups:
        for feature in group:
            values = group[feature]
            row = {
                "feature": feature, "count": int(values.count()), "mean": values.mean(),
                "median": values.median(), "std": values.std(ddof=1),
                "min": values.min(), "max": values.max(), "q25": values.quantile(0.25), "q75": values.quantile(0.75),
            }
            if label is not None:
                row["class_label"] = int(label)
            rows.append(row)
    return pd.DataFrame(rows)


def full_metrics(saved: dict[str, Any]) -> dict[str, Any]:
    (tn, fp), (fn, tp) = saved["confusion_matrix"]
    total = tn + fp + fn + tp
    return {
        **{key: saved[key] for key in ("threshold", "precision", "recall", "f1", "roc_auc", "pr_auc", "false_positive_rate")},
        "accuracy": (tn + tp) / total,
        "specificity": tn / (tn + fp),
        "false_negative_rate": fn / (fn + tp),
        "tn": tn, "fp": fp, "fn": fn, "tp": tp, "support": total,
    }


def verify_metrics(saved: dict[str, Any], computed: dict[str, Any]) -> None:
    for key, expected in saved.items():
        if key == "confusion_matrix":
            if expected != computed[key]:
                raise ValueError(f"Reconstructed confusion matrix differs: {expected} != {computed[key]}")
        elif isinstance(expected, (float, int)) and not np.isclose(expected, computed[key], rtol=1e-8, atol=1e-10):
            raise ValueError(f"Reconstructed {key} differs: {expected} != {computed[key]}")


def export_eda(
    directory: Path, kind: str, raw: pd.DataFrame, features: pd.DataFrame, labels: pd.Series, raw_target: str,
) -> None:
    positive = "Fraud" if kind == "fraud" else "Phishing"
    distributions = []
    for population, target in (("raw", raw[raw_target]), ("cleaned", labels)):
        for label, count in target.value_counts().sort_index().items():
            distributions.append({
                "population": population, "class_label": int(label),
                "class_name": positive if int(label) else "Legitimate",
                "count": int(count), "proportion": float(count / len(target)),
            })
    csv(directory / f"{kind}_class_distribution.csv", distributions)
    csv(directory / f"{kind}_missing_values.csv", [{
        "feature": column, "dtype": str(raw[column].dtype),
        "missing_count": int(raw[column].isna().sum()),
        "missing_percent": float(raw[column].isna().mean() * 100),
    } for column in raw])
    csv(directory / f"{kind}_raw_statistics.csv", statistics(raw))
    csv(directory / f"{kind}_raw_class_statistics.csv", statistics(raw.drop(columns=raw_target), raw[raw_target]))
    csv(directory / f"{kind}_cleaned_statistics.csv", statistics(features))
    csv(directory / f"{kind}_class_statistics.csv", statistics(features, labels))
    features.assign(target=labels).corr().rename_axis("feature").reset_index().to_csv(directory / f"{kind}_correlation.csv", index=False)
    raw.select_dtypes("number").corr().rename_axis("feature").reset_index().to_csv(directory / f"{kind}_raw_correlation.csv", index=False)
    histograms = []
    for population, frame, target in (("raw", raw.drop(columns=raw_target), raw[raw_target]), ("cleaned", features, labels)):
        for feature in frame.select_dtypes("number"):
            all_values = frame[feature].dropna().to_numpy(dtype=float)
            edges = np.histogram_bin_edges(all_values, bins=50)
            for label in sorted(target.unique()):
                values = frame.loc[target == label, feature].dropna().to_numpy(dtype=float)
                counts, _ = np.histogram(values, bins=edges)
                for left, right, count in zip(edges[:-1], edges[1:], counts, strict=True):
                    histograms.append({
                        "population": population, "feature": feature, "class_label": int(label),
                        "bin_left": float(left), "bin_right": float(right), "count": int(count),
                    })
    csv(directory / f"{kind}_histograms.csv", histograms)


def domain_audit(raw: pd.DataFrame, features: pd.DataFrame, splits: dict[str, pd.DataFrame]) -> dict[str, Any]:
    normalized: list[str] = []
    for value in raw["url"]:
        try:
            normalized.append(normalize_url(str(value).strip()))
        except ValueError:
            continue
    unique_urls = pd.Series(normalized).drop_duplicates().reset_index(drop=True)
    if len(unique_urls) != len(features):
        raise ValueError("Normalized URL alignment differs from training.")
    domains = unique_urls.map(lambda value: urlsplit(value).hostname)
    sets = {name: set(domains.loc[frame.index]) for name, frame in splits.items()}
    shared = sets["train"] & sets["test"]
    return {
        "train_unique_hostnames": len(sets["train"]), "validation_unique_hostnames": len(sets["validation"]),
        "test_unique_hostnames": len(sets["test"]), "train_test_shared_hostnames": len(shared),
        "test_rows_with_training_hostname": int(domains.loc[splits["test"].index].isin(sets["train"]).sum()),
        "test_rows": len(splits["test"]),
        "method": "Exact normalized hostname overlap, not registrable-domain grouping; no DNS or website fetch.",
    }


def export_shap(
    out: Path, kind: str, artifact: dict[str, Any], test: pd.DataFrame, labels: pd.Series,
    probability: np.ndarray, sample_size: int,
) -> dict[str, Any]:
    if sample_size < 20:
        raise ValueError("Use at least 20 SHAP sample rows.")
    indices = test.index.to_numpy()
    if len(test) > sample_size:
        indices, _ = train_test_split(indices, train_size=sample_size, stratify=labels, random_state=SEED)
    sample = test.loc[indices]
    explainer = build_explainer(artifact)
    transformed = artifact["pipeline"].named_steps["scale"].transform(sample)
    explained = explainer(transformed, check_additivity=True) if artifact["model_name"] != "logistic_regression" else explainer(transformed)
    values = np.asarray(explained.values)
    if values.ndim == 3:
        values = values[:, :, 1]
    bases = np.asarray(explained.base_values).reshape(-1)
    if len(bases) == 1:
        bases = np.repeat(bases, len(sample))
    sample_probability = artifact["pipeline"].predict_proba(sample)[:, 1]
    reconstructed = 1 / (1 + np.exp(-(bases + values.sum(axis=1))))
    if not np.allclose(sample_probability, reconstructed, atol=1e-5):
        raise ValueError("SHAP probability reconstruction failed.")
    records = [{
        "sample_id": int(index), "feature": feature, "value": float(sample.loc[index, feature]),
        "shap_value": float(values[row, column]), "target": int(labels.loc[index]),
        "probability": float(sample_probability[row]), "base_value": float(bases[row]),
    } for row, index in enumerate(sample.index) for column, feature in enumerate(sample.columns)]
    csv(out / "shap_analysis" / f"{kind}_values.csv", records)
    gain = getattr(artifact["pipeline"].named_steps["model"], "feature_importances_", np.full(len(sample.columns), np.nan))
    csv(out / f"{kind}_feature_importance.csv", [{
        "feature": feature, "mean_abs_shap": float(np.abs(values[:, column]).mean()),
        "mean_shap": float(values[:, column].mean()), "model_gain_importance": float(gain[column]),
        "n_samples": len(sample),
    } for column, feature in enumerate(sample.columns)])
    predicted = probability >= artifact["threshold"]
    outcomes = np.select([
        (labels.to_numpy() == 1) & predicted, (labels.to_numpy() == 0) & predicted,
        (labels.to_numpy() == 1) & ~predicted,
    ], ["TP", "FP", "FN"], default="TN")
    examples = []
    for outcome in ("TP", "FP", "FN", "TN"):
        positions = np.flatnonzero(outcomes == outcome)
        if not len(positions):
            continue
        position = int(positions[0])
        frame = test.iloc[[position]]
        transformed_case = artifact["pipeline"].named_steps["scale"].transform(frame)
        case = explainer(transformed_case, check_additivity=True) if artifact["model_name"] != "logistic_regression" else explainer(transformed_case)
        shap_values = np.asarray(case.values).reshape(-1)
        base = float(np.asarray(case.base_values).reshape(-1)[0])
        if not np.isclose(1 / (1 + np.exp(-(base + shap_values.sum()))), probability[position], atol=1e-5):
            raise ValueError(f"SHAP reconstruction failed for {kind} {outcome}.")
        for column, feature in enumerate(test.columns):
            examples.append({
                "case_id": f"{kind}_{outcome}", "outcome": outcome, "cleaned_row_index": int(frame.index[0]),
                "target": int(labels.iloc[position]), "probability": float(probability[position]),
                "prediction": int(predicted[position]), "base_value": base,
                "feature": feature, "value": float(frame.iloc[0, column]), "shap_value": float(shap_values[column]),
            })
    csv(out / "shap_analysis" / f"{kind}_examples.csv", examples)
    metadata = {
        "sample_size": len(sample), "sample_class_distribution": {str(key): int(value) for key, value in labels.loc[sample.index].value_counts().items()},
        "sampling": "Stratified held-out test sample, seed42; original feature values retained; no raw URLs exported.",
        "explainer": type(explainer).__name__, "explained_model": artifact["model_name"],
        "background_size": len(artifact["background"]), "units": "log-odds",
        "maximum_probability_reconstruction_error": float(np.abs(reconstructed - sample_probability).max()),
        "example_selection": "First held-out row in each actual outcome TP/FP/FN/TN; retrospective examples, not random representative cases.",
    }
    write_json(out / "shap_analysis" / f"{kind}_metadata.json", metadata)
    return metadata


def analyze(kind: str, out: Path, sample_size: int) -> dict[str, Any]:
    artifact = load_model(kind)
    saved = artifact["metrics"]
    dataset = ROOT / "data/raw" / ("transactions/creditcard.csv" if kind == "fraud" else "websites/phishing_features.csv")
    if digest(dataset) != saved["dataset_sha256"]:
        raise ValueError(f"{kind}: current raw CSV differs from saved training hash.")
    raw = read_dataset(dataset)
    if inspect_dataset(raw) != saved["inspection"]:
        raise ValueError(f"{kind}: dataset inspection differs from saved training evidence.")
    if kind == "fraud":
        features, labels, preparation = prepare_fraud(raw)
        target = "Class"
    else:
        prep = saved["preparation"]
        mapping = prep["label_mapping"]
        positive = next(label for label, meaning in mapping.items() if meaning == "phishing")
        negative = next(label for label, meaning in mapping.items() if meaning == "legitimate")
        target = prep["target_column"]
        features, labels, preparation = prepare_phishing(raw, prep["url_column"], target, positive, negative)
    if preparation != saved["preparation"] or list(features.columns) != artifact["features"]:
        raise ValueError(f"{kind}: preprocessing or ordered inference feature schema differs from training.")
    train_validation, test, y_train_validation, y_test = train_test_split(features, labels, test_size=0.2, stratify=labels, random_state=SEED)
    train, validation, y_train, y_validation = train_test_split(
        train_validation, y_train_validation, test_size=0.25, stratify=y_train_validation, random_state=SEED,
    )
    splits = {"train": train, "validation": validation, "test": test}
    targets = {"train": y_train, "validation": y_validation, "test": y_test}
    for name, frame in splits.items():
        if len(frame) != saved["split"][name]:
            raise ValueError(f"{kind}: {name} split size mismatch.")
    if not artifact["background"].equals(train.sample(min(100, len(train)), random_state=SEED)):
        raise ValueError(f"{kind}: saved SHAP background differs from reconstructed training split.")
    scale = artifact["pipeline"].named_steps["scale"]
    if not np.allclose(scale.mean_, train.mean().to_numpy(), rtol=1e-10, atol=1e-10):
        raise ValueError("Saved scaler was not fit to the reconstructed training mean.")
    split_rows = [{"cleaned_row_index": int(index), "split": name, "target": int(targets[name].loc[index])} for name, frame in splits.items() for index in frame.index]
    csv(out / "graph_data" / f"{kind}_split_assignments.csv", split_rows)
    export_eda(out / "graph_data", kind, raw, features, labels, target)
    rows = []
    for split_name, results in (("validation", saved["validation"]), ("test", saved["test_comparison"])):
        for name, result in results.items():
            rows.append({"model": name, "split": split_name, "selected": name == artifact["model_name"], **full_metrics(result)})
    csv(out / f"{kind}_model_results.csv", rows)
    csv(out / f"{kind}_confusion_matrix.csv", [{key: row[key] for key in ("model", "split", "tn", "fp", "fn", "tp", "threshold")} for row in rows])
    probabilities: dict[str, np.ndarray] = {}
    for name in ("validation", "test"):
        probabilities[name] = artifact["pipeline"].predict_proba(splits[name])[:, 1]
        verify_metrics(saved["validation"][artifact["model_name"]] if name == "validation" else saved["test"], evaluate(targets[name], probabilities[name], artifact["threshold"]))
    csv(out / "graph_data" / f"{kind}_heldout_scores.csv", {
        "cleaned_row_index": test.index, "target": y_test, "probability": probabilities["test"],
        "prediction": (probabilities["test"] >= artifact["threshold"]).astype(int),
    })
    fpr, tpr, roc_threshold = roc_curve(y_test, probabilities["test"], drop_intermediate=False)
    csv(out / f"{kind}_roc_data.csv", {"model": artifact["model_name"], "fpr": fpr, "tpr": tpr, "threshold": roc_threshold})
    precision, recall, pr_threshold = precision_recall_curve(y_test, probabilities["test"])
    csv(out / f"{kind}_pr_data.csv", {"model": artifact["model_name"], "precision": precision, "recall": recall, "threshold": np.append(pr_threshold, np.nan)})
    shap_meta = export_shap(out, kind, artifact, test, y_test, probabilities["test"], sample_size)
    metadata = {
        "selected_model": artifact["model_name"], "test_prevalence": float(y_test.mean()),
        "cleaned_class_distribution": saved["class_distribution"],
        "shap_sample_size": shap_meta["sample_size"], "shap_sample_description": shap_meta["sampling"],
    }
    write_json(out / "graph_data" / f"{kind}_metadata.json", metadata)
    parameters = {
        "selected_model": artifact["model_name"],
        "classifier": artifact["pipeline"].named_steps["model"].get_params(),
        "scaler": scale.get_params(),
        "anomaly": artifact["anomaly"].get_params() if artifact.get("anomaly") is not None else None,
    }
    write_json(out / "graph_data" / f"{kind}_parameters.json", parameters)
    temporal = None
    if kind == "fraud":
        temporal = {name: {"time_min": float(frame.Time.min()), "time_max": float(frame.Time.max())} for name, frame in splits.items()}
    domains = domain_audit(raw, features, splits) if kind == "phishing" else None
    result = {
        "source": SOURCES[kind], "dataset": str(dataset.relative_to(ROOT)), "dataset_sha256": saved["dataset_sha256"],
        "artifact_sha256": digest(model_directory() / f"{kind}.joblib"), "model_version": artifact["version"],
        "raw": inspect_dataset(raw), "preparation": preparation,
        "cleaned_rows": len(features), "input_features": list(features.columns),
        "raw_class_distribution": {str(label): int(count) for label, count in raw[target].value_counts().items()},
        "cleaned_class_distribution": saved["class_distribution"], "test_prevalence": float(y_test.mean()),
        "raw_imbalance_majority_to_minority": float(raw[target].value_counts().max() / raw[target].value_counts().min()),
        "cleaned_imbalance_majority_to_minority": float(labels.value_counts().max() / labels.value_counts().min()),
        "splits": {name: {"size": len(frame), "class_distribution": {str(label): int(count) for label, count in targets[name].value_counts().items()}} for name, frame in splits.items()},
        "saved_metrics_reproduced": True, "scaler_training_mean_verified": True, "background_verified": True,
        "parameters": parameters, "shap": shap_meta, "hostname_overlap": domains, "temporal_ranges": temporal,
        "constant_input_features": [feature for feature in features if features[feature].nunique() == 1],
        "metrics": rows,
        "unavailable": [
            "Original Logistic Regression fitted estimator and per-row scores were not saved; only validation/test aggregate results survive.",
            "No learning curves, epoch histories, calibration study, group/temporal holdout, external validation, or confidence intervals were saved.",
            "Isolation Forest was fit, but no anomaly-specific ground truth, evaluation metrics, or tuning experiment was saved.",
        ],
    }
    write_json(out / "graph_data" / f"{kind}_audit.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--shap-sample-size", type=int, default=512)
    args = parser.parse_args()
    for directory in (args.output, args.output / "graph_data", args.output / "shap_analysis"):
        directory.mkdir(parents=True, exist_ok=True)
    report = {}
    for kind in ("fraud", "phishing"):
        report[kind] = analyze(kind, args.output, args.shap_sample_size)
        print(f"{kind}: hash, split, saved metrics, scaler and SHAP verified; exports written.")
    manifest = {
        "created_at": datetime.now(UTC).isoformat(), "seed": SEED, "retrained_models": False,
        "command": "PYTHONPATH=backend backend/.venv/bin/python reports/ml_analysis/analyze.py",
        "versions": {"python": platform.python_version(), **{name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scikit-learn", "xgboost", "shap", "joblib")}},
        "datasets": {kind: {"source_sha256": item["dataset_sha256"], "artifact_sha256": item["artifact_sha256"], "model_version": item["model_version"]} for kind, item in report.items()},
        "scope": "Offline reproducibility audit. Application artifacts and datasets are read-only. No network or provider submissions.",
    }
    write_json(args.output / "manifest.json", manifest)


if __name__ == "__main__":
    main()
