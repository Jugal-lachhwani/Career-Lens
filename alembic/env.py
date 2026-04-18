"""
Alembic environment configuration for CareerLens.

Covers ALL SQLAlchemy/SQLModel models:
  - App models  : JobListing, JobAnalysis, SearchHistory, ChatSession, ChatMessage
  - Analytics   : JobRaw, JobFeatures
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env so DATABASE_URL is available even when running alembic from CLI
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Import ALL model metadata so Alembic can detect table changes
# ---------------------------------------------------------------------------
# App models (SQLModel / SQLAlchemy declarative base via SQLModel)
from sqlmodel import SQLModel
import src.models  # noqa: F401  — registers JobListing, JobAnalysis, SearchHistory, ChatSession, ChatMessage

# Analytics models (SQLAlchemy declarative base from src.Postres.postres)
from src.Postres.postres import Base as PostgresBase
import src.Postres.models  # noqa: F401  — registers JobRaw, JobFeatures

# Combine both metadata objects so --autogenerate covers everything
target_metadata = [SQLModel.metadata, PostgresBase.metadata]

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
config = context.config

# Build the URL from env vars (overrides whatever is in alembic.ini)
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "job_ai_agent")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ---------------------------------------------------------------------------
# Migration modes
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations without an actual DB connection (for SQL script output)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,          # Detect column type changes
            compare_server_default=True, # Detect server-default changes
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
