import uuid
from collections import defaultdict
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import models, schemas
from app.config import get_settings
from app.database import get_db, get_engine
from app.middleware import UploadBodyLimit
from app.providers import check_providers, provider_status
from app.reports import generate_pdf
from app.serializers import (
    investigation_detail,
    investigation_out,
    resource,
    scan_out,
    upload_detail,
    upload_out,
)
from app.uploads import normalize_merchant_url, parse_upload, validate_row

app = FastAPI(title="ExplainPay API", version="1.0.0")
app.add_middleware(UploadBodyLimit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
DB = Annotated[Session, Depends(get_db)]


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "; ".join(errors)})


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable; verify DATABASE_URL and apply Alembic migrations"},
    )


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def ml_call(method: str, *args: Any) -> Any:
    from app.ml import runtime

    try:
        return getattr(runtime, method)(*args)
    except runtime.ModelUnavailable as exc:
        # Runtime errors may contain local paths; its explicit model-unavailable reason is useful
        # locally, but credentials and tracebacks must never be returned.
        raise HTTPException(503, "Required ML model is unavailable; train and configure its artifacts") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def require(db: Session, entity, identity: uuid.UUID, *, lock: bool = False):
    statement = select(entity).where(entity.id == identity)
    if lock:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if item is None:
        raise HTTPException(404, "Resource not found")
    return item


def make_result(
    row: dict[str, Any], prediction: dict[str, Any], investigation_id: uuid.UUID,
    reference: str, upload_id: uuid.UUID | None = None,
) -> models.TransactionResult:
    return models.TransactionResult(
        upload_id=upload_id,
        investigation_id=investigation_id,
        transaction_reference=reference,
        amount=row["Amount"],
        **{
            field: prediction[field]
            for field in (
                "fraud_probability", "prediction", "risk_level", "threshold", "explanation",
                "base_value", "anomaly_score", "is_anomaly", "model_version",
            )
        },
        merchant_url=prediction.get("merchant_url") or row.get("merchant_url"),
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system/status")
def system_status() -> dict[str, Any]:
    from app.ml.runtime import model_status

    database: dict[str, Any] = {"available": False, "error": None}
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1 FROM alembic_version LIMIT 1"))
        database["available"] = True
    except (SQLAlchemyError, HTTPException, ValueError):
        database["error"] = "Database unavailable or migrations not applied"
    return {"database": database, "models": model_status(), "providers": provider_status()}


@app.post("/api/transactions/upload", response_model=schemas.UploadOut)
async def upload_transactions(db: DB, file: Annotated[UploadFile, File()]):
    filename, columns, rows = await parse_upload(file)
    investigation = models.Investigation(
        investigation_type="upload", title=f"Transaction batch: {filename}", status="pending"
    )
    db.add(investigation)
    db.flush()
    upload = models.Upload(
        investigation_id=investigation.id, filename=filename, columns=columns,
        rows=rows, total_records=len(rows),
    )
    db.add(upload)
    db.commit()
    return upload_out(upload)


@app.post("/api/transactions/analyze", response_model=schemas.UploadDetail)
def analyze_transactions(body: schemas.AnalyzeIn, db: DB):
    # PostgreSQL row lock serializes concurrent retries; all predictions and status commit together.
    upload = require(db, models.Upload, body.upload_id, lock=True)
    if upload.status == "completed":
        return upload_detail(db, upload)
    importance: dict[str, float] = defaultdict(float)
    risks = []
    for index, row in enumerate(upload.rows, start=1):
        prediction = ml_call("predict_transaction", row)
        result = make_result(
            row, prediction, upload.investigation_id, f"row-{index:06d}", upload.id
        )
        db.add(result)
        risks.append(result.risk_level)
        for contribution in prediction["explanation"]:
            importance[contribution["feature"]] += abs(contribution["contribution"])
    upload.feature_importance = [
        {"feature": feature, "importance": value / upload.total_records}
        for feature, value in sorted(importance.items(), key=lambda item: (-item[1], item[0]))
    ]
    upload.processed_records = upload.total_records
    upload.status = "completed"
    investigation = require(db, models.Investigation, upload.investigation_id)
    investigation.status = "completed"
    investigation.risk_level = max(
        risks, key=lambda risk: {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(risk.lower(), 0)
    )
    db.commit()
    return upload_detail(db, upload)


@app.post("/api/transactions/predict", response_model=schemas.TransactionOut)
def predict_transaction(body: schemas.PredictIn, db: DB):
    try:
        row = validate_row({**body.features, "merchant_url": body.merchant_url})
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    prediction = ml_call("predict_transaction", row)
    investigation = models.Investigation(
        investigation_type="transaction", title="Single transaction analysis",
        status="completed", risk_level=prediction["risk_level"],
    )
    db.add(investigation)
    db.flush()
    result = make_result(row, prediction, investigation.id, f"manual-{uuid.uuid4().hex}")
    db.add(result)
    db.commit()
    return result


@app.get("/api/transactions/history", response_model=list[schemas.UploadOut])
def transaction_history(db: DB):
    return [
        upload_out(upload)
        for upload in db.scalars(select(models.Upload).order_by(models.Upload.created_at.desc())).all()
    ]


@app.get("/api/transactions/metrics")
def transaction_metrics():
    return ml_call("metrics", "fraud")


@app.get("/api/transactions/uploads/{upload_id}", response_model=schemas.UploadDetail)
def get_upload(upload_id: uuid.UUID, db: DB):
    return upload_detail(db, require(db, models.Upload, upload_id))


@app.get("/api/transactions/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(transaction_id: uuid.UUID, db: DB):
    return require(db, models.TransactionResult, transaction_id)


@app.post("/api/websites/scan", response_model=schemas.ScanOut)
def scan_website(body: schemas.ScanIn, db: DB):
    try:
        normalized = normalize_merchant_url(body.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if normalized is None:
        raise HTTPException(422, "URL must not be empty")
    prediction = ml_call("predict_website", normalized)
    providers, findings = check_providers(normalized, prediction["normalized_domain"])
    investigation = models.Investigation(
        investigation_type="website", title=f"Website: {prediction['normalized_domain']}",
        status="completed", risk_level=prediction["risk_level"],
    )
    db.add(investigation)
    db.flush()
    scan = models.Scan(
        investigation_id=investigation.id,
        **prediction,
        scan_status="completed",
        providers=providers,
    )
    db.add(scan)
    db.flush()
    db.add_all([models.Finding(scan_id=scan.id, **finding) for finding in findings])
    db.commit()
    return scan_out(db, scan)


@app.get("/api/websites/history", response_model=list[schemas.ScanOut])
def website_history(db: DB):
    return [
        scan_out(db, scan)
        for scan in db.scalars(select(models.Scan).order_by(models.Scan.created_at.desc())).all()
    ]


@app.get("/api/websites/metrics")
def website_metrics():
    return ml_call("metrics", "phishing")


@app.get("/api/websites/{scan_id}", response_model=schemas.ScanOut)
def get_website(scan_id: uuid.UUID, db: DB):
    return scan_out(db, require(db, models.Scan, scan_id))


@app.get("/api/investigations", response_model=list[schemas.InvestigationOut])
def list_investigations(db: DB):
    investigations = db.scalars(
        select(models.Investigation).order_by(models.Investigation.created_at.desc())
    ).all()
    return [
        investigation_out(item, related.id if (related := resource(db, item)) else None)
        for item in investigations
    ]


@app.get("/api/investigations/{investigation_id}", response_model=schemas.InvestigationDetail)
def get_investigation(investigation_id: uuid.UUID, db: DB):
    return investigation_detail(db, require(db, models.Investigation, investigation_id))


@app.post("/api/reports/generate", response_model=schemas.ReportOut)
def create_report(body: schemas.ReportIn, db: DB):
    investigation = require(db, models.Investigation, body.investigation_id)
    report = models.Report(
        investigation_id=investigation.id, report_type="pdf",
        content=generate_pdf(investigation_detail(db, investigation)),
    )
    db.add(report)
    db.commit()
    return report


@app.get("/api/reports", response_model=list[schemas.ReportOut])
def list_reports(db: DB):
    return db.scalars(select(models.Report).order_by(models.Report.created_at.desc())).all()


@app.get("/api/reports/{report_id}/download")
def download_report(report_id: uuid.UUID, db: DB):
    report = require(db, models.Report, report_id)
    return Response(
        report.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="explainpay-{report.id}.pdf"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
