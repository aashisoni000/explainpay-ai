from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
GRAPH = ROOT / "graph_data"
SHAP = ROOT / "shap_analysis"
FIG = ROOT / "figures"


def style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
        }
    )


def save(fig: plt.Figure, rel: str, caption: str, entries: list[dict[str, str]]) -> None:
    out = FIG / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    entries.append({"file": str(out.relative_to(ROOT)), "caption": caption})


def class_distribution(kind: str, entries: list[dict[str, str]]) -> None:
    frame = pd.read_csv(GRAPH / f"{kind}_class_distribution.csv")
    pivot = frame.pivot(index="population", columns="class_name", values="count").fillna(0)
    fig, ax = plt.subplots(figsize=(7, 4))
    pivot.plot(kind="bar", ax=ax)
    ax.set_title(f"{kind.title()} class counts (raw vs cleaned)")
    ax.set_xlabel("Population")
    ax.set_ylabel("Rows")
    ax.tick_params(axis="x", rotation=0)
    save(
        fig,
        f"{kind}/{kind}_class_distribution.png",
        f"{kind.title()} dataset class counts before and after cleaning.",
        entries,
    )


def missing_values(kind: str, entries: list[dict[str, str]]) -> None:
    frame = pd.read_csv(GRAPH / f"{kind}_missing_values.csv")
    frame = frame[frame["missing_count"] > 0].sort_values("missing_count", ascending=False)
    if frame.empty:
        fig, ax = plt.subplots(figsize=(7, 2.5))
        ax.bar(["all_features"], [0], color="#4c78a8")
        ax.set_title(f"{kind.title()} missing values")
        ax.set_ylabel("Missing rows")
    else:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(frame["feature"], frame["missing_count"], color="#4c78a8")
        ax.set_title(f"{kind.title()} missing values")
        ax.set_ylabel("Missing rows")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    save(fig, f"{kind}/{kind}_missing_values.png", f"{kind.title()} missing-value counts by feature.", entries)


def distributions(kind: str, entries: list[dict[str, str]]) -> None:
    hist = pd.read_csv(GRAPH / f"{kind}_histograms.csv")
    importance = pd.read_csv(ROOT / f"{kind}_feature_importance.csv").sort_values("mean_abs_shap", ascending=False)
    top_features = importance["feature"].head(4).tolist()
    if kind == "fraud":
        top_features = ["Time", "Amount"] + [feature for feature in top_features if feature not in {"Time", "Amount"}][:2]
    else:
        top_features = [feature for feature in top_features if feature not in {"ip_hostname", "suspicious_tokens", "parameter_count", "suspicious_extension", "at_count", "encoded_count"}][:4]
    frame = hist[(hist["population"] == "cleaned") & (hist["feature"].isin(top_features))]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    axes = axes.ravel()
    palette = {0: "#4c78a8", 1: "#f58518"}
    for i, feature in enumerate(top_features):
        ax = axes[i]
        data = frame[frame["feature"] == feature].copy()
        data["mid"] = (data["bin_left"] + data["bin_right"]) / 2
        for label in sorted(data["class_label"].unique()):
            part = data[data["class_label"] == label]
            ax.plot(part["mid"], part["count"], label=f"class {label}", color=palette.get(label))
        ax.set_title(feature)
        ax.set_xlabel("Value")
        ax.set_ylabel("Count")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2)
    fig.suptitle(f"{kind.title()} cleaned distributions (top features)")
    save(
        fig,
        f"{kind}/{kind}_feature_distributions.png",
        f"{kind.title()} cleaned per-class distributions for top model-important numerical features.",
        entries,
    )


def correlation(kind: str, entries: list[dict[str, str]]) -> None:
    corr = pd.read_csv(GRAPH / f"{kind}_correlation.csv", index_col=0)
    score = corr.abs().sum(axis=1).sort_values(ascending=False)
    top = score.head(12).index.tolist()
    small = corr.loc[top, top]
    fig, ax = plt.subplots(figsize=(8, 7))
    mesh = ax.imshow(small.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(top, rotation=45, ha="right")
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top)
    ax.set_title(f"{kind.title()} correlation matrix (top 12 by absolute connectivity)")
    fig.colorbar(mesh, ax=ax, fraction=0.046, pad=0.04, label="Pearson r")
    save(fig, f"{kind}/{kind}_correlation_top12.png", f"{kind.title()} Pearson correlation heatmap for top 12 connected features.", entries)


def class_comparison(kind: str, entries: list[dict[str, str]]) -> None:
    stats = pd.read_csv(GRAPH / f"{kind}_class_statistics.csv")
    wide = (
        stats.pivot(index="feature", columns="class_label", values=["median", "q25", "q75"])
        .sort_index(axis=1)
        .copy()
    )
    wide.columns = [f"{name}_class{int(label)}" for name, label in wide.columns]
    wide["iqr_class0"] = wide["q75_class0"] - wide["q25_class0"]
    wide["iqr_class1"] = wide["q75_class1"] - wide["q25_class1"]
    wide["median_gap"] = (wide["median_class1"] - wide["median_class0"]).abs()
    top = wide.sort_values("median_gap", ascending=False).head(8).reset_index()
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(top))
    ax.errorbar(top["median_class0"], y - 0.12, xerr=top["iqr_class0"] / 2, fmt="o", label="class 0")
    ax.errorbar(top["median_class1"], y + 0.12, xerr=top["iqr_class1"] / 2, fmt="o", label="class 1")
    ax.set_yticks(y)
    ax.set_yticklabels(top["feature"])
    ax.set_xlabel("Median ± IQR/2")
    ax.set_title(f"{kind.title()} median/IQR comparison (largest class gaps)")
    ax.legend()
    save(fig, f"{kind}/{kind}_class_comparison.png", f"{kind.title()} feature-level class comparison using median and IQR.", entries)


def confusion_matrices(kind: str, entries: list[dict[str, str]]) -> None:
    cm = pd.read_csv(ROOT / f"{kind}_confusion_matrix.csv")
    test = cm[cm["split"] == "test"]
    fig, axes = plt.subplots(1, len(test), figsize=(10, 4))
    if len(test) == 1:
        axes = [axes]
    for ax, (_, row) in zip(axes, test.iterrows(), strict=False):
        matrix = np.array([[row["tn"], row["fp"]], [row["fn"], row["tp"]]])
        mesh = ax.imshow(matrix, cmap="Blues")
        ax.set_xticks([0, 1], labels=["Pred 0", "Pred 1"])
        ax.set_yticks([0, 1], labels=["True 0", "True 1"])
        ax.set_title(row["model"])
        for (i, j), value in np.ndenumerate(matrix):
            ax.text(j, i, int(value), ha="center", va="center", color="black")
    fig.colorbar(mesh, ax=axes, fraction=0.046, pad=0.04, label="Count")
    fig.suptitle(f"{kind.title()} test confusion matrices")
    save(fig, f"{kind}/{kind}_confusion_test_models.png", f"{kind.title()} test confusion matrices for both trained candidates.", entries)


def selected_curves(kind: str, entries: list[dict[str, str]]) -> None:
    roc = pd.read_csv(ROOT / f"{kind}_roc_data.csv")
    pr = pd.read_csv(ROOT / f"{kind}_pr_data.csv")
    selected = roc["model"].iloc[0]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(roc["fpr"], roc["tpr"], label=selected, color="#4c78a8")
    ax.plot([0, 1], [0, 1], linestyle="--", color="#999999", label="no-skill")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"{kind.title()} selected-model ROC")
    ax.legend()
    save(fig, f"{kind}/{kind}_roc_selected.png", f"{kind.title()} selected-model ROC curve on held-out test data.", entries)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(pr["recall"], pr["precision"], color="#f58518", label=selected)
    baseline = pr["precision"].iloc[0]
    ax.hlines(baseline, 0, 1, linestyle="--", color="#999999", label=f"no-skill ({baseline:.4f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(f"{kind.title()} selected-model precision-recall")
    ax.legend()
    save(fig, f"{kind}/{kind}_pr_selected.png", f"{kind.title()} selected-model precision-recall curve on held-out test data.", entries)


def performance(kind: str, entries: list[dict[str, str]]) -> None:
    results = pd.read_csv(ROOT / f"{kind}_model_results.csv")
    test = results[results["split"] == "test"].copy()
    metrics = ["accuracy", "roc_auc", "pr_auc", "precision", "recall", "f1", "specificity"]
    long = test.melt(id_vars=["model"], value_vars=metrics, var_name="metric", value_name="score")
    fig, ax = plt.subplots(figsize=(10, 5))
    for model in long["model"].unique():
        part = long[long["model"] == model]
        ax.plot(part["metric"], part["score"], marker="o", label=model)
    ax.set_ylim(0.0, 1.01)
    ax.set_title(f"{kind.title()} test metric comparison")
    ax.set_ylabel("Score")
    ax.tick_params(axis="x", rotation=25)
    ax.legend()
    save(fig, f"{kind}/{kind}_model_metrics_test.png", f"{kind.title()} held-out test metrics for both candidate models.", entries)

    fig, ax = plt.subplots(figsize=(8, 5))
    subset = long[long["metric"].isin(["precision", "recall", "f1"])]
    width = 0.35
    labels = ["precision", "recall", "f1"]
    x = np.arange(len(labels))
    for idx, model in enumerate(test["model"]):
        vals = [subset[(subset["model"] == model) & (subset["metric"] == m)]["score"].iloc[0] for m in labels]
        ax.bar(x + (idx - 0.5) * width, vals, width=width, label=model)
    ax.set_xticks(x, labels)
    ax.set_ylim(0.0, 1.01)
    ax.set_ylabel("Score")
    ax.set_title(f"{kind.title()} precision/recall/F1 comparison")
    ax.legend()
    save(fig, f"{kind}/{kind}_precision_recall_f1_test.png", f"{kind.title()} precision, recall, and F1 comparison across candidates.", entries)


def feature_importance(kind: str, entries: list[dict[str, str]]) -> None:
    imp = pd.read_csv(ROOT / f"{kind}_feature_importance.csv").sort_values("mean_abs_shap", ascending=True)
    top = imp.tail(12)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top["feature"], top["mean_abs_shap"], color="#4c78a8")
    ax.set_xlabel("Mean absolute SHAP value (log-odds)")
    ax.set_title(f"{kind.title()} global SHAP importance (top 12)")
    save(fig, f"{kind}/{kind}_shap_importance_top12.png", f"{kind.title()} global feature importance from mean absolute SHAP values.", entries)

    top_gain = imp.sort_values("model_gain_importance", ascending=True).tail(12)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top_gain["feature"], top_gain["model_gain_importance"], color="#f58518")
    ax.set_xlabel("XGBoost gain importance")
    ax.set_title(f"{kind.title()} model gain importance (top 12)")
    save(fig, f"{kind}/{kind}_gain_importance_top12.png", f"{kind.title()} XGBoost gain importance for top features.", entries)


def shap_beeswarm(kind: str, entries: list[dict[str, str]]) -> None:
    values = pd.read_csv(SHAP / f"{kind}_values.csv")
    top = (
        values.groupby("feature")["shap_value"]
        .apply(lambda series: series.abs().mean())
        .sort_values(ascending=False)
        .head(10)
        .index
        .tolist()
    )
    data = values[values["feature"].isin(top)].copy()
    order = {feature: idx for idx, feature in enumerate(reversed(top))}
    rng = np.random.default_rng(42)
    fig, ax = plt.subplots(figsize=(9, 6))
    for feature in top:
        part = data[data["feature"] == feature]
        y = np.full(len(part), order[feature]) + rng.normal(0, 0.08, len(part))
        scatter = ax.scatter(part["shap_value"], y, c=part["value"], s=10, alpha=0.55, cmap="coolwarm")
    ax.set_yticks(range(len(top)), list(reversed(top)))
    ax.axvline(0, color="#666666", linewidth=1)
    ax.set_xlabel("SHAP value (log-odds contribution)")
    ax.set_title(f"{kind.title()} SHAP beeswarm (sampled held-out rows)")
    color = fig.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)
    color.set_label("Feature value")
    save(fig, f"{kind}/{kind}_shap_beeswarm_top10.png", f"{kind.title()} SHAP beeswarm for top features on sampled held-out rows.", entries)


def waterfalls(kind: str, entries: list[dict[str, str]]) -> None:
    examples = pd.read_csv(SHAP / f"{kind}_examples.csv")
    for outcome in ["TP", "FP", "FN", "TN"]:
        part = examples[examples["outcome"] == outcome].copy()
        if part.empty:
            continue
        top = part.reindex(part["shap_value"].abs().sort_values(ascending=False).index).head(10).iloc[::-1]
        fig, ax = plt.subplots(figsize=(8, 5))
        colors = ["#4c78a8" if value >= 0 else "#e45756" for value in top["shap_value"]]
        ax.barh(top["feature"], top["shap_value"], color=colors)
        row = part.iloc[0]
        ax.set_title(
            f"{kind.title()} {outcome} case (p={row['probability']:.6f}, target={int(row['target'])}, pred={int(row['prediction'])})"
        )
        ax.set_xlabel("SHAP contribution (log-odds)")
        save(
            fig,
            f"{kind}/{kind}_waterfall_{outcome.lower()}.png",
            f"{kind.title()} {outcome} example with top SHAP feature contributions.",
            entries,
        )


def main() -> None:
    style()
    entries: list[dict[str, str]] = []
    for kind in ("fraud", "phishing"):
        class_distribution(kind, entries)
        missing_values(kind, entries)
        distributions(kind, entries)
        correlation(kind, entries)
        class_comparison(kind, entries)
        confusion_matrices(kind, entries)
        selected_curves(kind, entries)
        performance(kind, entries)
        feature_importance(kind, entries)
        shap_beeswarm(kind, entries)
        waterfalls(kind, entries)
    pd.DataFrame(entries).to_csv(FIG / "captions.csv", index=False)
    print(f"Generated {len(entries)} figures in {FIG}")


if __name__ == "__main__":
    main()
