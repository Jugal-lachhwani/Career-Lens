# src/Database/database.py
import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

# Import models so SQLModel knows them when create_all runs
from src.models import JobListing, JobAnalysis, SearchHistory, ChatSession, ChatMessage  # noqa: F401

load_dotenv()

DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "job_ai_agent")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,        # Connections kept open in the pool
    max_overflow=20,     # Extra connections allowed under burst
    pool_timeout=30,     # Seconds to wait for a connection before raising
    pool_recycle=1800,   # Recycle connections every 30 min (avoids stale TCP)
    pool_pre_ping=True,  # Test connection on checkout — handles DB restarts
)


def init_db():
    """Create all tables that don't already exist. Idempotent."""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session