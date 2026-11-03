"""Explicit opt-in new experiments; never overwrite application model artifacts."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.model_selection import StratifiedKFold, learning_curve, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze import (
    ROOT,
    SEED,
    csv,
    digest,
    evaluate,
    load_model,
    prepare_fraud,
    prepare_phishing,
    read_dataset,
    verify_metrics,
)


def inputs(kind: str) -> tuple[pd.DataFrame, pd.Series]:
    saved = load_model(kind)["metrics"]
    path = ROOT / "data/raw" / ("transactions/creditcard.csv" if kind == "fraud" else "websites/phishing_features.csv")
    if digest(path) != saved["dataset_sha256"]:
        raise ValueError("Current dataset differs from the original training input.")
    raw = read_dataset(path)
    if kind == "fraud":
        features, labels, _ = prepare_fraud(raw)
    else:
        prep = saved["preparation"]
        features, labels, _ = prepare_phishing(raw, prep["url_column"], prep["target_column"], "1", "0")
    train_validation, _, y_train_validation, _ = train_test_split(features, labels, test_size=0.2, stratify=labels, random_state=SEED)
    train, _, y_train, _ = train_test_split(train_validation, y_train_validation, test_size=0.25, stratify=y_train_validation, random_state=SEED)
    return train, y_train


def recover_baselines(output: Path) -> None:
    for kind in ("fraud", "phishing"):
        artifact = load_model(kind)
        audit = json.loads((HERE / "graph_data" / f"{kind}_audit.json").read_text())
        path = ROOT / audit["dataset"]
        if digest(path) != audit["dataset_sha256"]:
            raise ValueError("Dataset hash differs; first regenerate and validate the analysis pack.")
        raw = read_dataset(path)
        features, labels, _ = prepare_fraud(raw) if kind == "fraud" else prepare_phishing(raw, "url", "label", "1", "0")
        train_validation, test, y_train_validation, y_test = train_test_split(features, labels, test_size=0.2, stratify=labels, random_state=SEED)
        train, validation, y_train, y_validation = train_test_split(train_validation, y_train_validation, test_size=0.25, stratify=y_train_validation, random_state=SEED)
        pipeline = Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))])
        pipeline.fit(train, y_train)
        threshold = artifact["metrics"]["validation"]["logistic_regression"]["threshold"]
        scores = pipeline.predict_proba(test)[:, 1]
        verify_metrics(artifact["metrics"]["test_comparison"]["logistic_regression"], evaluate(y_test, scores, threshold))
        verify_metrics(artifact["metrics"]["validation"]["logistic_regression"], evaluate(y_validation, pipeline.predict_proba(validation)[:, 1], threshold))
        fpr, tpr, thresholds = roc_curve(y_test, scores, drop_intermediate=False)
        csv(output / f"{kind}_reconstructed_baseline_roc.csv", {"fpr": fpr, "tpr": tpr, "threshold": thresholds})
        precision, recall, thresholds = precision_recall_curve(y_test, scores)
        csv(output / f"{kind}_reconstructed_baseline_pr.csv", {"precision": precision, "recall": recall, "threshold": np.append(thresholds, np.nan)})
        csv(output / f"{kind}_reconstructed_baseline_coefficients.csv", {"feature": features.columns, "scaled_log_odds_coefficient": pipeline.named_steps["model"].coef_[0]})
        print(f"{kind}: NEW baseline reconstruction matched original aggregate metrics; files labelled reconstructed.")


def new_learning_curves(output: Path) -> None:
    for kind in ("fraud", "phishing"):
        features, labels = inputs(kind)
        estimator = clone(load_model(kind)["pipeline"])
        sizes, training_scores, validation_scores = learning_curve(
            estimator, features, labels,
            cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED),
            train_sizes=[0.1, 0.25, 0.5, 0.75, 1.0], scoring="average_precision",
            shuffle=True, random_state=SEED, n_jobs=1, error_score="raise",
        )
        csv(output / f"{kind}_new_learning_curve.csv", [{
            "training_rows": int(size), "fold": fold,
            "training_average_precision": float(training_scores[index, fold]),
            "validation_average_precision": float(validation_scores[index, fold]),
        } for index, size in enumerate(sizes) for fold in range(3)])
        print(f"{kind}: NEW training-only 3-fold AP learning-curve experiment; original test set untouched.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=["recover-baselines", "learning-curves"])
    args = parser.parse_args()
    output = HERE / "new_experiments" / args.experiment
    output.mkdir(parents=True, exist_ok=True)
    if args.experiment == "recover-baselines":
        recover_baselines(output)
    else:
        new_learning_curves(output)


if __name__ == "__main__":
    main()
