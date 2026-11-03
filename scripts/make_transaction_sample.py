"""Export a small, genuinely sourced CSV for UI demonstration, not evaluation."""

import argparse
import json
from pathlib import Path

from app.ml.runtime import ROOT
from app.ml.train import prepare_fraud, read_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=ROOT / "data/raw/transactions/creditcard.csv")
    parser.add_argument("--per-class", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.per_class <= 100:
        parser.error("--per-class must be between 1 and 100.")
    try:
        features, labels, _ = prepare_fraud(read_dataset(args.path))
        data = features.assign(Class=labels)
        if data["Class"].value_counts().min() < args.per_class:
            parser.error("Not enough real rows of each class for the requested sample.")
        sample = data.groupby("Class", group_keys=False).sample(n=args.per_class, random_state=42)
        output = ROOT / "data/processed"
        output.mkdir(parents=True, exist_ok=True)
        path = output / "ulb_sample_transactions.csv"
        sample.to_csv(path, index=False)
        path.with_suffix(".provenance.json").write_text(json.dumps({
            "source": "Actual user-downloaded ULB creditcard.csv",
            "rows": len(sample),
            "purpose": "Interface demonstration only; not held-out evaluation.",
            "warning": "Source labels do not guarantee any model's prediction. No merchant identity is available.",
        }, indent=2), encoding="utf-8")
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
    print(f"Saved {len(sample)} actual dataset rows to {path}")


if __name__ == "__main__":
    main()
