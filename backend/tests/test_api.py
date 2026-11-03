import json
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.database import get_db
from app.main import app
from app.ml import runtime
from app.uploads import REQUIRED_COLUMNS
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from test_uploads import csv_data

from app import models


def prediction(row):
    # Deterministic API test double only; production never substitutes for trained models.
    return {
        "fraud_probability": 0.9,
        "prediction": 1,
        "risk_level": "high",
        "threshold": 0.5,
        "explanation": [{"feature": "Amount", "value": row["Amount"], "contribution": 0.2}],
        "base_value": -0.3,
        "anomaly_score": None,
        "is_anomaly": None,
        "model_version": "test-artifact",
        "merchant_url": row.get("merchant_url"),
    }


@pytest.fixture
def predicted(monkeypatch):
    monkeypatch.setattr(runtime, "predict_transaction", prediction)


def upload(client, rows=2):
    response = client.post(
        "/api/transactions/upload",
        files={"file": ("sample.csv", csv_data([[0] * 29 + [42]] * rows), "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_health_validation_and_safe_database_error():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}

        def unused_db():
            with Session() as session:
                yield session

        app.dependency_overrides[get_db] = unused_db
        try:
            invalid = client.post("/api/websites/scan", json={"url": ""})
            assert invalid.status_code == 422
            assert isinstance(invalid.json()["detail"], str)
        finally:
            app.dependency_overrides.clear()

        def broken_db():
            raise OperationalError("private connection", {}, RuntimeError("secret password"))
            yield

        app.dependency_overrides[get_db] = broken_db
        try:
            result = client.get("/api/reports")
            assert result.status_code == 503
            assert "secret" not in result.text
        finally:
            app.dependency_overrides.clear()


def test_persistent_batch_idempotency_history_and_report(client, db_engine, predicted):
    batch = upload(client)
    analyzed = client.post("/api/transactions/analyze", json={"upload_id": batch["id"]})
    assert analyzed.status_code == 200, analyzed.text
    detail = analyzed.json()
    assert detail["summary"] == {"total": 2, "flagged": 2, "legitimate": 0, "high_risk": 2}
    assert detail["processed_records"] == 2
    assert detail["feature_importance"] == [{"feature": "Amount", "importance": 0.2}]
    retry = client.post("/api/transactions/analyze", json={"upload_id": batch["id"]})
    assert retry.json() == detail
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(models.TransactionResult)) == 2
    assert client.get("/api/transactions/history").json()[0]["id"] == batch["id"]
    assert client.get(f"/api/transactions/uploads/{batch['id']}").json() == detail
    result_id = detail["results"][0]["id"]
    assert client.get(f"/api/transactions/{result_id}").json()["amount"] == 42
    inv = client.get(f"/api/investigations/{batch['investigation_id']}").json()
    assert inv["upload"]["id"] == batch["id"]
    assert inv["resource_id"] == batch["id"]
    assert inv["status"] == "completed"
    report = client.post(
        "/api/reports/generate", json={"investigation_id": batch["investigation_id"]}
    )
    assert report.status_code == 200, report.text
    pdf = client.get(f"/api/reports/{report.json()['id']}/download")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")
    assert pdf.headers["content-type"] == "application/pdf"
    assert client.get("/api/reports").json()[0]["id"] == report.json()["id"]


def test_concurrent_analysis_has_no_duplicate_rows(client, db_engine, predicted):
    batch = upload(client)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: client.post(
                    "/api/transactions/analyze", json={"upload_id": batch["id"]}
                ), range(2),
            )
        )
    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json() == responses[1].json()
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(models.TransactionResult)) == 2


def test_analysis_failure_rolls_back_every_result(client, db_engine, monkeypatch):
    batch = upload(client)
    calls = 0

    def fail_second(row):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise runtime.ModelUnavailable("missing secret local artifact")
        return prediction(row)

    monkeypatch.setattr(runtime, "predict_transaction", fail_second)
    response = client.post("/api/transactions/analyze", json={"upload_id": batch["id"]})
    assert response.status_code == 503
    assert "secret" not in response.text
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(models.TransactionResult)) == 0
        saved = session.get(models.Upload, uuid.UUID(batch["id"]))
        assert saved.status == "pending"
        assert saved.processed_records == 0


def test_single_prediction_and_required_fields(client, predicted):
    features = {name: 0 for name in REQUIRED_COLUMNS}
    response = client.post(
        "/api/transactions/predict",
        json={"features": features, "merchant_url": "https://example.com"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["upload_id"] is None
    assert result["merchant_url"] == "https://example.com/"
    inv = client.get(f"/api/investigations/{result['investigation_id']}").json()
    assert inv["transaction"]["id"] == result["id"]
    assert client.post("/api/transactions/predict", json={"features": {}}).status_code == 422
    assert client.post(
        "/api/transactions/predict", json={"features": {**features, "Time": -1}}
    ).status_code == 422
    for invalid_number in (True, False, "1", "NaN", "Infinity"):
        invalid = client.post(
            "/api/transactions/predict",
            json={"features": {**features, "V2": invalid_number}},
        )
        assert invalid.status_code == 422, invalid.text
    assert client.post(
        "/api/transactions/predict",
        json={"features": features, "merchant_url": "http://localhost"},
    ).status_code == 422


def test_upload_request_errors_and_pending_report(client, db_engine):
    assert client.post("/api/transactions/upload").status_code == 422
    invalid = client.post(
        "/api/transactions/upload", files={"file": ("bad.csv", b"private\nsecret\n")}
    )
    assert invalid.status_code == 422
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(models.Investigation)) == 0
    batch = upload(client)
    response = client.post(
        "/api/reports/generate", json={"investigation_id": batch["investigation_id"]}
    )
    assert response.status_code == 200
    assert client.get(f"/api/reports/{response.json()['id']}/download").content.startswith(b"%PDF-")


def test_upload_byte_limits_are_checked_before_persistence(client, db_engine, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 100)
    response = client.post(
        "/api/transactions/upload", files={"file": ("sample.csv", b"x" * 101)}
    )
    assert response.status_code == 413
    response = client.post(
        "/api/transactions/upload", files={"file": ("sample.csv", b"x" * 70000)}
    )
    assert response.status_code == 413
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(models.Upload)) == 0


@pytest.mark.parametrize(
    "path",
    ["/api/transactions/", "/api/transactions/uploads/", "/api/websites/",
     "/api/investigations/", "/api/reports/"],
)
def test_missing_records(client, path):
    url = f"{path}{uuid.uuid4()}"
    if path == "/api/reports/":
        url += "/download"
    response = client.get(url)
    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found"}


def test_website_persistence_and_provider_status(client, monkeypatch):
    from app.ml.urls import extract_features, normalize_url

    def website_prediction(url):
        return {
            "url": normalize_url(url), "normalized_domain": "example.com",
            "ml_probability": 0.1, "ml_prediction": 0, "risk_level": "low", "threshold": 0.5,
            "explanation": [{"feature": "url_length", "value": 20.0, "contribution": 0.1}],
            "base_value": -0.2,
            "features": extract_features(url), "model_version": "test-website-artifact",
        }

    monkeypatch.setattr(runtime, "predict_website", website_prediction)
    monkeypatch.setattr(
        "app.main.check_providers",
        lambda url, domain: (
            [{"name": "virustotal", "status": "unavailable", "details": {}}],
            [{
                "finding_type": "reputation", "severity": "medium", "description": "Test evidence",
                "evidence": {"suspicious": 1}, "source": "test",
            }],
        ),
    )
    response = client.post("/api/websites/scan", json={"url": "https://example.com"})
    assert response.status_code == 200, response.text
    scan = response.json()
    assert json.loads(scan["findings"][0]["evidence"])["suspicious"] == 1
    assert scan["providers"][0]["status"] == "unavailable"
    assert client.get(f"/api/websites/{scan['id']}").json() == scan
    assert client.get("/api/websites/history").json()[0] == scan
    detail = client.get(f"/api/investigations/{scan['investigation_id']}").json()
    assert detail["website"] == scan
    assert client.post("/api/websites/scan", json={"url": "file:///etc/passwd"}).status_code == 422
    assert client.post("/api/websites/scan", json={"url": "http://127.0.0.1"}).status_code == 422


def test_model_missing_metrics_and_prediction_return_503(client, monkeypatch):
    def unavailable(*args):
        raise runtime.ModelUnavailable("No trained artifact")

    monkeypatch.setattr(runtime, "metrics", unavailable)
    monkeypatch.setattr(runtime, "predict_transaction", unavailable)
    assert client.get("/api/transactions/metrics").status_code == 503
    assert client.post(
        "/api/transactions/predict",
        json={"features": {name: 0 for name in REQUIRED_COLUMNS}},
    ).status_code == 503
