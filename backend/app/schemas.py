import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Record(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_created_at(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class Explanation(BaseModel):
    feature: str
    value: float
    contribution: float


class TransactionOut(Record):
    upload_id: uuid.UUID | None
    investigation_id: uuid.UUID
    transaction_reference: str
    amount: float
    fraud_probability: float
    prediction: int
    risk_level: str
    threshold: float
    explanation: list[Explanation]
    base_value: float
    anomaly_score: float | None
    is_anomaly: bool | None
    model_version: str
    merchant_url: str | None


class UploadOut(Record):
    filename: str
    total_records: int
    processed_records: int
    status: str
    columns: list[str]
    preview: list[dict[str, Any]]
    investigation_id: uuid.UUID


class Summary(BaseModel):
    total: int
    flagged: int
    legitimate: int
    high_risk: int


class Importance(BaseModel):
    feature: str
    importance: float


class UploadDetail(UploadOut):
    results: list[TransactionOut]
    summary: Summary
    feature_importance: list[Importance]


class AnalyzeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    upload_id: uuid.UUID


class PredictIn(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    features: dict[str, Annotated[float, Field(strict=True)]]
    merchant_url: str | None = Field(default=None, max_length=2048)


class ScanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2048)


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    finding_type: str
    severity: str
    description: str
    evidence: dict[str, Any]
    source: str


class ProviderOut(BaseModel):
    name: str
    status: str
    details: dict[str, Any]


class ScanOut(Record):
    investigation_id: uuid.UUID
    url: str
    normalized_domain: str
    ml_probability: float
    ml_prediction: int
    risk_level: str
    threshold: float
    explanation: list[Explanation]
    base_value: float | None = None
    features: dict[str, float]
    model_version: str
    scan_status: str
    findings: list[FindingOut]
    providers: list[ProviderOut]


class InvestigationOut(Record):
    investigation_type: str
    title: str
    status: str
    risk_level: str | None
    updated_at: datetime
    resource_id: uuid.UUID | None

    @field_validator("updated_at")
    @classmethod
    def utc_updated_at(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class InvestigationDetail(InvestigationOut):
    upload: UploadDetail | None = None
    transaction: TransactionOut | None = None
    website: ScanOut | None = None


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    investigation_id: uuid.UUID


class ReportOut(Record):
    investigation_id: uuid.UUID
    report_type: str


class ErrorOut(BaseModel):
    detail: str
