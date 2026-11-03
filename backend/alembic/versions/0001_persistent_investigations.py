"""Create persistent investigations and evidence.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def identity():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    op.create_table(
        "users", *identity(),
        sa.Column("display_name", sa.String(120), nullable=False),
    )
    op.create_table(
        "investigations", *identity(),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("investigation_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("risk_level", sa.String(30)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "investigation_type IN ('upload', 'transaction', 'website')",
            name="ck_investigation_type",
        ),
        sa.CheckConstraint("status IN ('pending', 'completed')", name="ck_investigation_status"),
    )
    op.create_index("ix_investigations_user_id", "investigations", ["user_id"])
    op.create_index("ix_investigations_created_at", "investigations", ["created_at"])
    op.create_table(
        "uploads", *identity(),
        sa.Column("investigation_id", sa.Uuid(),
                  sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=False),
        sa.Column("processed_records", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("columns", postgresql.JSONB(), nullable=False),
        sa.Column("rows", postgresql.JSONB(), nullable=False),
        sa.Column("feature_importance", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("total_records > 0 AND total_records <= 5000", name="ck_upload_total"),
        sa.CheckConstraint(
            "processed_records >= 0 AND processed_records <= total_records",
            name="ck_upload_processed",
        ),
        sa.CheckConstraint("status IN ('pending', 'completed')", name="ck_upload_status"),
    )
    op.create_index("ix_uploads_investigation_id", "uploads", ["investigation_id"], unique=True)
    op.create_index("ix_uploads_created_at", "uploads", ["created_at"])
    op.create_table(
        "results", *identity(),
        sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("uploads.id", ondelete="CASCADE")),
        sa.Column("investigation_id", sa.Uuid(),
                  sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_reference", sa.String(80), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("fraud_probability", sa.Float(), nullable=False),
        sa.Column("prediction", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(30), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False),
        sa.Column("base_value", sa.Float(), nullable=False),
        sa.Column("anomaly_score", sa.Float()),
        sa.Column("is_anomaly", sa.Boolean()),
        sa.Column("model_version", sa.String(255), nullable=False),
        sa.Column("merchant_url", sa.Text()),
        sa.UniqueConstraint("upload_id", "transaction_reference", name="uq_result_upload_reference"),
        sa.CheckConstraint("amount >= 0", name="ck_result_amount"),
        sa.CheckConstraint("fraud_probability BETWEEN 0 AND 1", name="ck_result_probability"),
        sa.CheckConstraint("threshold BETWEEN 0 AND 1", name="ck_result_threshold"),
        sa.CheckConstraint("prediction IN (0, 1)", name="ck_result_prediction"),
    )
    op.create_index("ix_results_upload_id", "results", ["upload_id"])
    op.create_index("ix_results_investigation_id", "results", ["investigation_id"])
    op.create_table(
        "scans", *identity(),
        sa.Column("investigation_id", sa.Uuid(),
                  sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_domain", sa.String(253), nullable=False),
        sa.Column("ml_probability", sa.Float(), nullable=False),
        sa.Column("ml_prediction", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(30), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False),
        sa.Column("base_value", sa.Float()),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("model_version", sa.String(255), nullable=False),
        sa.Column("scan_status", sa.String(30), nullable=False),
        sa.Column("providers", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("ml_probability BETWEEN 0 AND 1", name="ck_scan_probability"),
        sa.CheckConstraint("threshold BETWEEN 0 AND 1", name="ck_scan_threshold"),
        sa.CheckConstraint("ml_prediction IN (0, 1)", name="ck_scan_prediction"),
    )
    op.create_index("ix_scans_investigation_id", "scans", ["investigation_id"], unique=True)
    op.create_index("ix_scans_normalized_domain", "scans", ["normalized_domain"])
    op.create_index("ix_scans_created_at", "scans", ["created_at"])
    op.create_table(
        "findings", *identity(),
        sa.Column("scan_id", sa.Uuid(), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
    )
    op.create_index("ix_findings_scan_id", "findings", ["scan_id"])
    op.create_table(
        "reports", *identity(),
        sa.Column("investigation_id", sa.Uuid(),
                  sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )
    op.create_index("ix_reports_investigation_id", "reports", ["investigation_id"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])


def downgrade():
    for table in ("reports", "findings", "scans", "results", "uploads", "investigations", "users"):
        op.drop_table(table)
