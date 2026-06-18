"""Alembic environment configuration for Karsa.

Supports both offline (SQL script) and online (live database) migration modes.
Database URL is sourced exclusively from the POSTGRES_URL environment variable.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# ---------------------------------------------------------------------------
# Logging — honour the [loggers] section in alembic.ini when present
# ---------------------------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata — import the project's declarative Base so that
# autogenerate can compare the model definitions against the live schema.
# ---------------------------------------------------------------------------
# Import all models to ensure they are registered against the metadata before
# autogenerate inspects it.
from karsa.shared.persistence.base import Base  # noqa: E402

# Import all model modules so their tables are registered on Base.metadata.
# Add new bounded-context model imports here as features are added.
try:
    import karsa.shared.persistence  # noqa: F401
except ImportError:
    pass

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Database URL — sourced from the environment variable POSTGRES_URL.
# Override the value set in alembic.ini (which reads env:POSTGRES_URL) so
# that the URL is always resolved at runtime, never hard-coded.
# ---------------------------------------------------------------------------
def get_url() -> str:
    url = os.environ.get("POSTGRES_URL")
    if not url:
        raise RuntimeError(
            "POSTGRES_URL environment variable is not set. "
            "Set it before running Alembic commands."
        )
    return url


# ---------------------------------------------------------------------------
# Offline migration mode — generates SQL script without a live DB connection.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout/file)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode — runs migrations against a live database connection.
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    # Build engine config, injecting the runtime URL
    ini_section = config.get_section(config.config_ini_section, {})
    ini_section["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point — Alembic calls this module; choose mode automatically.
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
