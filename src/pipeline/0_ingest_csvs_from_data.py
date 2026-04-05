"""
Phase 0: Ingest pre-scraped LinkedIn CSVs

Reads all `dataset_linkedin-jobs-scraper_*.csv` files from `src/data/`
and inserts them into the PostgreSQL `jobs_raw` table using the existing
`ingest_raw_jobs` helper.

This lets you run Phase 2 (Ollama skill extraction) on top of CSV data
without re-running the Apify scraper.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

from src.Postres.postres import SessionLocal
from src.pipeline.ingest_operations import ingest_raw_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _clean_value(value: Any) -> Any:
    """Convert pandas missing values (NaN/NaT) to None for DB/JSON safety."""
    if pd.isna(value):
        return None
    return value


def load_csv_jobs(data_dir: Path) -> List[Dict[str, Any]]:
    """Load all dataset_linkedin-jobs-scraper_*.csv files into a list of dicts.

    The dict schema is compatible with what `ingest_raw_jobs` expects from
    the Apify actor output (id, title, companyName, location, etc.).
    """
    csv_files = sorted(data_dir.glob("dataset_linkedin-jobs-scraper_*.csv"))

    if not csv_files:
        logger.warning(f"No CSV files found in {data_dir}")
        return []

    all_jobs: List[Dict[str, Any]] = []

    for csv_path in csv_files:
        logger.info(f"📥 Loading CSV: {csv_path.name}")
        df = pd.read_csv(csv_path)

        # Normalize column names we care about; CSV already matches Apify schema
        for _, row in df.iterrows():
            row_data = {k: _clean_value(v) for k, v in row.to_dict().items()}

            # jobs_raw deduplicates by id, so skip rows that don't have one.
            raw_id = row_data.get("id")
            if raw_id in (None, ""):
                continue

            job: Dict[str, Any] = {
                "id": str(raw_id),
                "title": row_data.get("title"),
                "companyName": row_data.get("companyName"),
                "location": row_data.get("location"),
                "experienceLevel": row_data.get("experienceLevel"),
                "contractType": row_data.get("contractType"),
                "salary": row_data.get("salary"),
                "description": row_data.get("description"),
                # Keep full raw record as close as possible to original
                "url": row_data.get("url"),
                "postedDate": row_data.get("postedDate"),
                "applicationsCount": row_data.get("applicationsCount"),
                "applyType": row_data.get("applyType"),
                "applyUrl": row_data.get("applyUrl"),
                "companyUrl": row_data.get("companyUrl"),
                "descriptionHtml": row_data.get("descriptionHtml"),
                "postedTimeAgo": row_data.get("postedTimeAgo"),
                "recruiterName": row_data.get("recruiterName"),
                "recruiterUrl": row_data.get("recruiterUrl"),
                "sector": row_data.get("sector"),
                "workType": row_data.get("workType"),
            }
            all_jobs.append(job)

        logger.info(f"✅ Loaded {len(df)} rows from {csv_path.name}")

    logger.info(f"📦 Total jobs loaded from CSVs: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    # Resolve src/data directory relative to this file
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "src" / "data"

    logger.info(f"🔎 Scanning for CSVs in {data_dir}...")
    jobs_data = load_csv_jobs(data_dir)

    if not jobs_data:
        logger.warning("Nothing to ingest; exiting.")
        raise SystemExit(0)

    db = SessionLocal()
    try:
        logger.info("🚀 Ingesting CSV jobs into jobs_raw via ingest_raw_jobs()...")
        inserted = ingest_raw_jobs(db, jobs_data)
        db.commit()
        logger.info(f"✅ Phase 0 Complete! Inserted {len(inserted)} new job records into jobs_raw.")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to ingest CSV jobs: {e}", exc_info=True)
        raise
    finally:
        db.close()
