import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Identity:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Identity, Base):
    __tablename__ = "users"
    display_name: Mapped[str] = mapped_column(String(120))


class Investigation(Identity, Base):
    __tablename__ = "investigations"
    __table_args__ = (
        CheckConstraint(
            "investigation_type IN ('upload', 'transaction', 'website')",
            name="ck_investigation_type",
        ),
        CheckConstraint("status IN ('pending', 'completed')", name="ck_investigation_status"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    investigation_type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    risk_level: Mapped[str | None] = mapped_column(String(30))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Upload(Identity, Base):
    __tablename__ = "uploads"
    __table_args__ = (
        CheckConstraint("total_records > 0 AND total_records <= 5000", name="ck_upload_total"),
        CheckConstraint(
            "processed_records >= 0 AND processed_records <= total_records",
            name="ck_upload_processed",
        ),
        CheckConstraint("status IN ('pending', 'completed')", name="ck_upload_status"),
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), unique=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    total_records: Mapped[int] = mapped_column(Integer)
    processed_records: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    columns: Mapped[list[str]] = mapped_column(JSONB)
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    feature_importance: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class TransactionResult(Identity, Base):
    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("upload_id", "transaction_reference", name="uq_result_upload_reference"),
        CheckConstraint("amount >= 0", name="ck_result_amount"),
        CheckConstraint("fraud_probability BETWEEN 0 AND 1", name="ck_result_probability"),
        CheckConstraint("threshold BETWEEN 0 AND 1", name="ck_result_threshold"),
        CheckConstraint("prediction IN (0, 1)", name="ck_result_prediction"),
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("uploads.id", ondelete="CASCADE"), index=True
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    transaction_reference: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Float)
    fraud_probability: Mapped[float] = mapped_column(Float)
    prediction: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(30))
    threshold: Mapped[float] = mapped_column(Float)
    explanation: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    base_value: Mapped[float] = mapped_column(Float)
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    is_anomaly: Mapped[bool | None]
    model_version: Mapped[str] = mapped_column(String(255))
    merchant_url: Mapped[str | None] = mapped_column(Text)


class Scan(Identity, Base):
    __tablename__ = "scans"
    __table_args__ = (
        CheckConstraint("ml_probability BETWEEN 0 AND 1", name="ck_scan_probability"),
        CheckConstraint("threshold BETWEEN 0 AND 1", name="ck_scan_threshold"),
        CheckConstraint("ml_prediction IN (0, 1)", name="ck_scan_prediction"),
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), unique=True, index=True
    )
    url: Mapped[str] = mapped_column(Text)
    normalized_domain: Mapped[str] = mapped_column(String(253), index=True)
    ml_probability: Mapped[float] = mapped_column(Float)
    ml_prediction: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(30))
    threshold: Mapped[float] = mapped_column(Float)
    explanation: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    base_value: Mapped[float | None] = mapped_column(Float)
    features: Mapped[dict[str, float]] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(String(255))
    scan_status: Mapped[str] = mapped_column(String(30), default="completed")
    providers: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class Finding(Identity, Base):
    __tablename__ = "findings"
    scan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True
    )
    finding_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(80))


class Report(Identity, Base):
    __tablename__ = "reports"
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    report_type: Mapped[str] = mapped_column(String(30), default="pdf")
    content: Mapped[bytes] = mapped_column(LargeBinary)


Index("ix_investigations_created_at", Investigation.created_at)
Index("ix_uploads_created_at", Upload.created_at)
Index("ix_scans_created_at", Scan.created_at)
Index("ix_reports_created_at", Report.created_at)
