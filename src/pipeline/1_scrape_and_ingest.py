"""
Phase 1: Job Scraping and Storage

Uses Apify to scrape LinkedIn based on specified configuration, and
stores the exact API responses as raw logs in PostgreSQL.
"""
import logging
import argparse
from src.tools.scraping_tools import job_scraping
from src.Postres.postres import SessionLocal
from src.pipeline.ingest_operations import ingest_raw_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape and ingest LinkedIn jobs.")
    parser.add_argument("--title", type=str, default="", help="Job title to search for")
    parser.add_argument("--location", type=str, default="India", help="Location to search in")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of jobs to fetch")
    args = parser.parse_args()

    actor_input = {
        "title": "AI engineer",
        "location": "India",
        "datePosted": "r2592000",  # last 30 days
        "limit": 50,
    }

    logger.info(f"🚀 Starting Apify actor for {actor_input['limit']} jobs in {actor_input['location']}...")
    jobs_data = job_scraping(actor_input, wait_seconds=600)

    if not jobs_data:
        logger.warning("⚠️ No jobs returned from Apify")
        exit(1)

    logger.info(f"📦 Fetched {len(jobs_data)} jobs from Apify. Ingesting to DB...")
    
    db = SessionLocal()
    try:
        raw_jobs = ingest_raw_jobs(db, jobs_data)
        db.commit()
        logger.info(f"✅ Phase 1 Complete! Inserted {len(raw_jobs)} job records into jobs_raw.")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to ingest raw jobs: {e}", exc_info=True)
    finally:
        db.close()
