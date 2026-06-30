import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Engine — with production-grade connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,        # Connections kept open in the pool
    max_overflow=20,     # Extra connections under burst
    pool_timeout=30,     # Seconds to wait before "no connection" error
    pool_recycle=1800,   # Recycle every 30 min (prevents stale TCP)
    pool_pre_ping=True,  # Test connection on checkout — handles DB restarts
)

# Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()