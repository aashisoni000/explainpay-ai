"""Real-artifact API integration; synthetic fixtures are never production models."""

import argparse
import shutil
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from app.config import get_settings
from app.ml import runtime
from app.ml.train import train


@pytest.fixture
def trained_models(db_engine, monkeypatch):
    # Keep every fixture under the project and remove it even if training fails.
    directory = Path(__file__).resolve().parents[1] / f".test-models-{uuid.uuid4().hex}"
    directory.mkdir()
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(rng.normal(size=(80, 30)), columns=runtime.TRANSACTION_FEATURES)
    frame["Time"] = np.arange(80)
    frame["Amount"] = np.abs(frame["Amount"])
    frame["Class"] = np.tile([0, 1], 40)
    phishing = pd.DataFrame([
        {
            "address": (
                f"https://store-{index}.com/catalog"
                if label == "legitimate"
                else f"http://verify-login-{index}.com/account?verify=1"
            ),
            "target": label,
        }
        for index in range(40)
        for label in ("legitimate", "phishing")
    ])
    settings = get_settings()
    monkeypatch.setattr(settings, "virustotal_api_key", "")
    monkeypatch.setattr(settings, "google_webrisk_api_key", "")
    monkeypatch.setattr(settings, "rdap_enabled", False)
    monkeypatch.setenv("MODEL_DIR", str(directory))
    runtime.load_model.cache_clear()
    runtime._explainer.cache_clear()
    try:
        for kind, data in (("fraud", frame), ("phishing", phishing)):
            path = directory / f"SYNTHETIC_TEST_ONLY_{kind}.csv"
            data.to_csv(path, index=False)
            train(argparse.Namespace(
                kind=kind, path=str(path), inspect=False, output=str(directory),
                url_column="address" if kind == "phishing" else None,
                target_column="target" if kind == "phishing" else None,
                positive_label="phishing" if kind == "phishing" else None,
                negative_label="legitimate" if kind == "phishing" else None,
            ))
        yield frame.drop(columns=["Class"])
    finally:
        runtime.load_model.cache_clear()
        runtime._explainer.cache_clear()
        shutil.rmtree(directory)


def assert_additivity(result, probability_key):
    log_odds = result["base_value"] + sum(
        entry["contribution"] for entry in result["explanation"]
    )
    assert 1 / (1 + np.exp(-log_odds)) == pytest.approx(
        result[probability_key], abs=1e-5
    )


def test_trained_runtime_database_reports_and_idempotency(client, trained_models):
    frame = trained_models
    single = client.post(
        "/api/transactions/predict",
        json={"features": frame.iloc[0].to_dict(), "merchant_url": "https://example.com"},
    )
    assert single.status_code == 200, single.text
    assert_additivity(single.json(), "fraud_probability")
    assert len(single.json()["explanation"]) == 30

    uploaded = client.post(
        "/api/transactions/upload",
        files={"file": ("SYNTHETIC_TEST_ONLY.csv", frame.head(3).to_csv(index=False).encode())},
    )
    assert uploaded.status_code == 200, uploaded.text
    analyzed = client.post(
        "/api/transactions/analyze", json={"upload_id": uploaded.json()["id"]}
    )
    assert analyzed.status_code == 200, analyzed.text
    detail = analyzed.json()
    assert len(detail["results"]) == 3
    for result in detail["results"]:
        assert_additivity(result, "fraud_probability")
    assert client.post(
        "/api/transactions/analyze", json={"upload_id": detail["id"]}
    ).json() == detail

    scanned = client.post("/api/websites/scan", json={"url": "https://store-999.com/catalog"})
    assert scanned.status_code == 200, scanned.text
    assert len(scanned.json()["explanation"]) == 15
    assert_additivity(scanned.json(), "ml_probability")
    assert all(
        provider["status"] in {"not_configured", "disabled"}
        for provider in scanned.json()["providers"]
    )
    assert client.get(f"/api/websites/{scanned.json()['id']}").json() == scanned.json()
    metrics = client.get("/api/transactions/metrics")
    assert metrics.status_code == 200
    assert "confusion_matrix" in metrics.json()["test"]
    for investigation_id in (
        single.json()["investigation_id"],
        detail["investigation_id"],
        scanned.json()["investigation_id"],
    ):
        report = client.post(
            "/api/reports/generate", json={"investigation_id": investigation_id}
        )
        assert report.status_code == 200, report.text
        downloaded = client.get(f"/api/reports/{report.json()['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF-")
