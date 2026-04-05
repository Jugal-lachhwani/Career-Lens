# src/database/models.py
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Postres.postres import Base


class JobRaw(Base):
    __tablename__ = "jobs_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Helpful for deduplication if Apify gives an ID
    apify_job_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    salary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Store exact actor output here
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    scraped_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    feature: Mapped["JobFeatures"] = relationship(
        back_populates="job_raw",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_jobs_raw_company_location", "company_name", "location"),
    )


class JobFeatures(Base):
    __tablename__ = "job_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    job_raw_id: Mapped[int] = mapped_column(
        ForeignKey("jobs_raw.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Copy only useful fields for analytics
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    salary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    posted_date: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Extracted feature
    skills: Mapped[list] = mapped_column(JSONB, nullable=False)

    extracted_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job_raw: Mapped["JobRaw"] = relationship(back_populates="feature")

    __table_args__ = (
        Index("ix_job_features_company_location", "company_name", "location"),
    )

