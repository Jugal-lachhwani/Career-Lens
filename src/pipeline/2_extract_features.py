"""
Phase 2: Job Feature Extraction

Queries unanalyzed `jobs_raw` entries from PostgreSQL,
processes each using Ollama AI to extract strict feature data,
and logs the extracted features into `job_features`.
"""
import logging
from src.Postres.postres import SessionLocal
from src.Postres.models import JobRaw, JobFeatures
from src.pipeline.ingest_operations import extract_and_store_features
from src.agents import Agents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    db = SessionLocal()
    agents = Agents()
    
    try:
        # Find raw jobs that don't have an associated feature extracted yet
        logger.info("🔍 Querying for unprocessed raw jobs...")
        unprocessed_jobs = (
            db.query(JobRaw)
            .outerjoin(JobFeatures, JobRaw.id == JobFeatures.job_raw_id)
            .filter(JobFeatures.id == None)
            .all()
        )
        
        if not unprocessed_jobs:
            logger.info("✅ All jobs have been processed. Nothing to do.")
            exit(0)
            
        logger.info(f"🚀 Extracting features for {len(unprocessed_jobs)} jobs using Ollama...")
        features = extract_and_store_features(db, unprocessed_jobs, agents)
        db.commit()
        logger.info(f"✅ Phase 2 Complete! Extracted and stored {len(features)} jobs features.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to extract features: {e}", exc_info=True)
    finally:
        db.close()
