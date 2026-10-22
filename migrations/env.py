"""Alembic entry point: use explicit migration credentials, never log the URL."""

from alembic import context
from sqlalchemy import create_engine, pool

from quotation_app.config import Settings
from quotation_app.persistence.models import Base

target_metadata = Base.metadata
url = Settings().migration_url()

if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
