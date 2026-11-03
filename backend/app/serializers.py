import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


def upload_out(upload: models.Upload) -> schemas.UploadOut:
    return schemas.UploadOut(
        id=upload.id,
        created_at=upload.created_at,
        filename=upload.filename,
        total_records=upload.total_records,
        processed_records=upload.processed_records,
        status=upload.status,
        columns=upload.columns,
        preview=upload.rows[:5],
        investigation_id=upload.investigation_id,
    )


def upload_detail(db: Session, upload: models.Upload) -> schemas.UploadDetail:
    results = db.scalars(
        select(models.TransactionResult)
        .where(models.TransactionResult.upload_id == upload.id)
        .order_by(models.TransactionResult.created_at, models.TransactionResult.transaction_reference)
    ).all()
    flagged = sum(result.prediction == 1 for result in results)
    return schemas.UploadDetail(
        **upload_out(upload).model_dump(),
        results=[schemas.TransactionOut.model_validate(result) for result in results],
        summary=schemas.Summary(
            total=len(results),
            flagged=flagged,
            legitimate=len(results) - flagged,
            high_risk=sum(result.risk_level.lower() in {"high", "critical"} for result in results),
        ),
        feature_importance=upload.feature_importance,
    )


def scan_out(db: Session, scan: models.Scan) -> schemas.ScanOut:
    findings = db.scalars(
        select(models.Finding).where(models.Finding.scan_id == scan.id)
        .order_by(models.Finding.created_at, models.Finding.id)
    ).all()
    fields = {
        field: getattr(scan, field)
        for field in schemas.ScanOut.model_fields
        if field != "findings"
    }
    return schemas.ScanOut(
        **fields,
        findings=[schemas.FindingOut.model_validate(finding) for finding in findings],
    )


def resource(db: Session, investigation: models.Investigation):
    kind = investigation.investigation_type
    entity = {"upload": models.Upload, "transaction": models.TransactionResult, "website": models.Scan}[
        kind
    ]
    return db.scalar(select(entity).where(entity.investigation_id == investigation.id))


def investigation_out(
    investigation: models.Investigation, resource_id: uuid.UUID | None
) -> schemas.InvestigationOut:
    return schemas.InvestigationOut(
        **{
            field: getattr(investigation, field)
            for field in schemas.InvestigationOut.model_fields
            if field != "resource_id"
        },
        resource_id=resource_id,
    )


def investigation_detail(
    db: Session, investigation: models.Investigation
) -> schemas.InvestigationDetail:
    related = resource(db, investigation)
    result = schemas.InvestigationDetail(
        **investigation_out(investigation, related.id if related else None).model_dump()
    )
    if isinstance(related, models.Upload):
        result.upload = upload_detail(db, related)
    elif isinstance(related, models.TransactionResult):
        result.transaction = schemas.TransactionOut.model_validate(related)
    elif isinstance(related, models.Scan):
        result.website = scan_out(db, related)
    return result
