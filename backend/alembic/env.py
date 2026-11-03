from alembic import context
from app.config import get_settings
from app.database import engine_for_url
from app.models import Base

config = context.config
target_metadata = Base.metadata
url = get_settings().database_url
connection = config.attributes.get("connection")
if not url and connection is None:
    raise RuntimeError("DATABASE_URL must be set before running migrations")


if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
elif connection is not None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine_for_url(url).connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()
