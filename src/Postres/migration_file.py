# alembic/versions/xxxxxxxx_create_job_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "xxxxxxxx"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "jobs_raw",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("apify_job_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("experience_level", sa.String(length=100), nullable=True),
        sa.Column("contract_type", sa.String(length=100), nullable=True),
        sa.Column("salary", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("apify_job_id", name="uq_jobs_raw_apify_job_id"),
    )
    op.create_index("ix_jobs_raw_id", "jobs_raw", ["id"])
    op.create_index("ix_jobs_raw_apify_job_id", "jobs_raw", ["apify_job_id"])
    op.create_index("ix_jobs_raw_company_name", "jobs_raw", ["company_name"])
    op.create_index("ix_jobs_raw_location", "jobs_raw", ["location"])

    op.create_table(
        "job_features",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "job_raw_id",
            sa.Integer(),
            sa.ForeignKey("jobs_raw.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("experience_level", sa.String(length=100), nullable=True),
        sa.Column("contract_type", sa.String(length=100), nullable=True),
        sa.Column("salary", sa.String(length=255), nullable=True),
        sa.Column("job_url", sa.String(length=512), nullable=True),
        sa.Column("posted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_job_features_job_raw_id", "job_features", ["job_raw_id"])
    op.create_index("ix_job_features_company_name", "job_features", ["company_name"])
    op.create_index("ix_job_features_location", "job_features", ["location"])


def downgrade():
    op.drop_index("ix_job_features_location", table_name="job_features")
    op.drop_index("ix_job_features_company_name", table_name="job_features")
    op.drop_index("ix_job_features_job_raw_id", table_name="job_features")
    op.drop_table("job_features")

    op.drop_index("ix_jobs_raw_location", table_name="jobs_raw")
    op.drop_index("ix_jobs_raw_company_name", table_name="jobs_raw")
    op.drop_index("ix_jobs_raw_apify_job_id", table_name="jobs_raw")
    op.drop_index("ix_jobs_raw_id", table_name="jobs_raw")
    op.drop_table("jobs_raw")