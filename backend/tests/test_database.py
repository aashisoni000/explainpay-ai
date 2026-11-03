import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models


def test_migration_matches_declared_schema(db_engine):
    with db_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, models.Base.metadata) == []


def test_foreign_keys_and_upload_constraints_are_enforced(db_engine):
    with Session(db_engine) as session:
        session.add(models.Upload(
            investigation_id=uuid.uuid4(), filename="test.csv", total_records=1,
            processed_records=0, status="pending", columns=[], rows=[],
        ))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        investigation = models.Investigation(
            investigation_type="upload", title="Constraint validation", status="pending"
        )
        session.add(investigation)
        session.flush()
        session.add(models.Upload(
            investigation_id=investigation.id, filename="test.csv", total_records=0,
            processed_records=0, status="pending", columns=[], rows=[],
        ))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert session.scalar(select(models.Investigation)) is None
