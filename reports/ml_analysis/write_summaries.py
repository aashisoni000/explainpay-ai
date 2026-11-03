"""Render research summaries from audited CSV/JSON; no model training."""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent

URL_MEANINGS = {
    "url_length": "Character count of normalized URL, including scheme and query; fragment removed.",
    "domain_length": "Length of normalized ASCII/IDNA hostname.",
    "dot_count": "Dot characters anywhere in normalized URL, not only hostname.",
    "subdomain_count": "max(hostname dot-separated labels minus 2, 0); 0 for IP. Not public-suffix-aware.",
    "hyphen_count": "Hyphens anywhere in normalized URL.",
    "digit_count": "Characters for which Python str.isdigit() is true in normalized URL.",
    "ip_hostname": "1 if hostname parses as a public IP; otherwise 0.",
    "https": "1 for normalized HTTPS scheme; encryption is not a safety guarantee.",
    "suspicious_tokens": "Count of distinct substrings present: login, verify, secure, account, update, bank, wallet, password.",
    "parameter_count": "Parsed query pairs, including blank values, using urllib.parse.parse_qsl.",
    "suspicious_extension": "Path ends with .exe, .zip, .scr, .apk, or .js, case insensitive.",
    "url_entropy": "Shannon character entropy (bits/character) of normalized URL.",
    "path_length": "Character count of URL path (default /).",
    "at_count": "@ characters anywhere; credential URLs are already rejected.",
    "encoded_count": "Percent-sign characters; this is not a validated count of encoded bytes.",
}
RAW_URL_MEANINGS = {
    "url": "Source URL string; normalized and validated before feature recomputation.",
    "label": "Publisher encoding: 1 phishing, 0 benign.",
    "url_length": "Publisher: total source URL length; NOT used directly by the trained pipeline.",
    "num_dots": "Publisher: number of dots; extractor details not included in repository.",
    "has_https": "Publisher: HTTPS indicator; source values not used in inference.",
    "has_ip": "Publisher: IP-in-URL indicator; differs from our hostname parser.",
    "num_subdirs": "Publisher: slash count; not an actual parsed subdomain count.",
    "num_params": "Publisher: question-mark/ampersand count, not our parsed parameter pairs.",
    "suspicious_words": "Publisher suspicious-token feature; exact source token list unavailable.",
    "tld": "Publisher top-level domain; 821 missing values, unused by selected preprocessing.",
    "special_char_count": "Publisher count of -_%@=~ characters; source implementation not saved.",
    "digits_count": "Publisher digit count; source implementation not saved.",
    "entropy": "Publisher URL entropy; source normalization details unavailable.",
}


def table(frame: pd.DataFrame) -> str:
    def cell(value: object) -> str:
        if pd.isna(value):
            return "undefined"
        if isinstance(value, float):
            return f"{value:.8g}"
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(map(str, frame.columns)) + " |", "| " + " | ".join("---" for _ in frame.columns) + " |"]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in frame.itertuples(index=False, name=None))
    return "\n".join(lines)


def main() -> None:
    sections = [
        "# ExplainPay: verified dataset and model evidence",
        ("Generated from `graph_data/*_audit.json` and CSV exports. Full precision lives in CSVs; prose tables round for readability. "
        "Sources and models were read locally. No retraining, URL visits, or external provider submissions occurred."),
        ("## Reproducibility\n"
        "Raw SHA-256, ordered feature schema, exact cleaning results, 60/20/20 stratified split "
        "(seed 42), saved 100-row SHAP background, training-only scaler means, and selected "
        "validation/test predictions were checked against artifacts. A discrepancy aborts extraction. "
        "Cleaned row indices in split and explanation files are local analysis identifiers, not original "
        "merchant/transaction IDs. Histogram counts cover complete ranges; standard deviation uses ddof=1. "
        "Correlations are Pearson coefficients; constant-column correlations would be undefined, never replaced with zero."),
    ]
    dictionary = []
    for kind, title in (("fraud", "ULB credit card transactions"), ("phishing", "Phishing URLs with extracted features")):
        data = json.loads((HERE / "graph_data" / f"{kind}_audit.json").read_text())
        raw = data["raw"]
        sections.extend([
            f"## {title}",
            (f"Source: {data['source']}\n\nLocal input: `{data['dataset']}`\n\n"
            f"Raw size: **{raw['rows']:,} rows x {len(raw['columns'])} columns**. "
            f"Cleaned size: **{data['cleaned_rows']:,} rows x {len(data['input_features'])} input features**, plus binary target.\n\n"
            f"Raw majority/minority ratio: **{data['raw_imbalance_majority_to_minority']:.6f}:1**. "
            f"Cleaned ratio: **{data['cleaned_imbalance_majority_to_minority']:.6f}:1**. "
            "The majority class is legitimate for fraud and phishing for the URL dataset."),
            "### Class distribution\n" + table(pd.read_csv(HERE / "graph_data" / f"{kind}_class_distribution.csv")),
            "### Missing values, types, and schema\n" + table(pd.read_csv(HERE / "graph_data" / f"{kind}_missing_values.csv")),
            f"Exact duplicate source rows: **{raw['duplicate_rows']:,}**. Cleaning record:\n```json\n{json.dumps(data['preparation'], indent=2)}\n```",
            "### Raw numerical statistics\nAll numeric columns including target; mean/median/std/min/max "
            "are descriptive, not fitted preprocessing. Target statistics summarize prevalence, not a feature.\n\n"
            + table(pd.read_csv(HERE / "graph_data" / f"{kind}_raw_statistics.csv")),
            "### Actual model-input numerical statistics\n"
            + table(pd.read_csv(HERE / "graph_data" / f"{kind}_cleaned_statistics.csv")),
            "### Train / validation / test split\n" + table(pd.DataFrame([
                {"split": name, "total": item["size"], "class_0": item["class_distribution"].get("0", 0), "class_1": item["class_distribution"].get("1", 0)}
                for name, item in data["splits"].items()
            ])),
            "### Feature meanings",
        ])
        if kind == "fraud":
            meanings = {
                "Time": "Seconds elapsed since the first source transaction; random splits overlap in time.",
                **{f"V{i}": "Anonymized PCA component. Original variable, loadings and semantic interpretation are unavailable." for i in range(1, 29)},
                "Amount": "Source transaction amount; upstream ULB documentation describes euros. Application conservatively displays supplied amount without assuming currency for arbitrary uploads.",
                "Class": "Binary target: 1 fraudulent, 0 legitimate. Excluded from model inputs.",
            }
        else:
            meanings = RAW_URL_MEANINGS
        rows = [{"feature": name, "meaning": meaning, "population": "source"} for name, meaning in meanings.items()]
        if kind == "phishing":
            rows.extend({"feature": name, "meaning": meaning, "population": "recomputed_model_input"} for name, meaning in URL_MEANINGS.items())
        dictionary.extend({"task": kind, **row} for row in rows)
        sections.append(table(pd.DataFrame(rows)))
        sections.extend([
            "### Every trained supervised candidate: validation and held-out test\n"
            "Accuracy, specificity and false-negative rate below are computed exactly from saved confusion counts; "
            "other metrics are retained from the original experiment. Logistic Regression metrics are historical "
            "aggregates; its fitted estimator was not serialized.\n\n"
            + table(pd.read_csv(HERE / f"{kind}_model_results.csv")),
            "### SHAP sampling and explainers\n```json\n" + json.dumps(data["shap"], indent=2) + "\n```",
            "### Top global SHAP contributions\nMean absolute log-odds contribution on the documented "
            "512-row test sample, not the complete population. Gain importance is a different model-internal quantity.\n\n"
            + table(pd.read_csv(HERE / f"{kind}_feature_importance.csv").sort_values("mean_abs_shap", ascending=False)),
        ])
        if data["hostname_overlap"]:
            sections.append("### Actual hostname overlap audit\n```json\n" + json.dumps(data["hostname_overlap"], indent=2) + "\n```\n"
                            "This is a URL-level random holdout, NOT an unseen-domain benchmark. Exact URL deduplication "
                            "does not prevent related domains/paths from crossing splits.")
        if data["temporal_ranges"]:
            sections.append("### Actual time ranges\n```json\n" + json.dumps(data["temporal_ranges"], indent=2) + "\n```\n"
                            "No chronological/forward-looking fraud evaluation was conducted.")
    sections.extend([
        "## Graph-ready data inventory",
        ("- `graph_data/*_class_distribution.csv`: raw and cleaned class counts/proportions.\n"
        "- `graph_data/*_histograms.csv`: complete 50-bin per-class feature distributions for source and cleaned numeric inputs.\n"
        "- `graph_data/*_raw_statistics.csv`, `*_cleaned_statistics.csv`: all numerical summaries.\n"
        "- `graph_data/*_raw_class_statistics.csv`, `*_class_statistics.csv`: class-conditioned means, medians, standard deviations, ranges and quartiles.\n"
        "- `graph_data/*_raw_correlation.csv`, `*_correlation.csv`: raw/cleaned Pearson matrices; target associations are descriptive, not causal.\n"
        "- `graph_data/*_missing_values.csv`: every source column, including zero missing counts.\n"
        "- `graph_data/*_split_assignments.csv`, `*_heldout_scores.csv`: exact local cleaned indices, split membership and selected-model test scores.\n"
        "- Root `*_model_results.csv`, `*_confusion_matrix.csv`, `*_roc_data.csv`, `*_pr_data.csv`: actual saved/reproduced supervised results.\n"
        "- `shap_analysis/*_values.csv`: long-form beeswarm data; original feature values and log-odds SHAP values, no URL strings.\n"
        "- `shap_analysis/*_examples.csv`: complete per-feature explanations for one actual TP/FP/FN/TN case where present.\n"
        "- `graph_data/*_parameters.json`: fitted pipeline configurations; JSON string `nan` denotes XGBoost's missing-value sentinel, not a fabricated numeric result.\n"
        "- `manifest.json`: input/artifact hashes, versions and audit execution metadata."),
        "## Scientific cautions",
        ("1. Fraud has only 95 positive test examples; 24 are missed by selected XGBoost.\n"
        "2. Phishing test prevalence is about 99.2%; its no-skill AP baseline is already about 0.992. "
        "Very high AP/F1 must not hide 37 false alarms among only 164 benign test examples.\n"
        "3. Logistic Regression has lower phishing benign false-positive rate (20/164) than selected XGBoost (37/164). "
        "Selection followed validation AP, not specificity. Do not reselect or retune using these test results.\n"
        "4. SHAP global sampling preserves prevalence: fraud 511 negative/1 positive, phishing 4 negative/508 positive. "
        "These rankings are dominated by the majority population; class-conditioned explanation studies remain needed.\n"
        "5. High confidence scores are not calibrated probabilities. No probability-calibration or confidence-interval experiment was saved.\n"
        "6. Exact domain overlap, random time overlap, source imbalance and the URL rejection policy limit external validity."),
    ])
    (HERE / "dataset_summary.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    pd.DataFrame(dictionary).to_csv(HERE / "graph_data" / "feature_dictionary.csv", index=False)
    print("Dataset summary and complete feature dictionary written from audited exports.")


if __name__ == "__main__":
    main()
