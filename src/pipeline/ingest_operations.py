"""
Data Ingestion & Extraction Operations.

Contains functions to insert raw data and extract analytical features.
"""

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.Postres.models import JobRaw, JobFeatures
from src.agents import Agents

logger = logging.getLogger(__name__)

# Safety limits for Ollama / LLM calls
LLM_MAX_RETRIES = 3
LLM_RETRY_SLEEP_SECONDS = 2
LLM_TIMEOUT_SECONDS = 60  # per-job upper bound in seconds
USE_SYNTHETIC_SKILLS_ONLY = os.getenv("USE_SYNTHETIC_SKILLS_ONLY", "false").lower() in {
    "1",
    "true",
    "yes",
}

SYNTHETIC_MAX_SKILLS = 12
SYNTHETIC_SKILL_KEYWORDS = {
    "python": ["python", "pandas", "numpy", "scipy"],
    "sql": ["sql", "postgres", "mysql", "sqlite", "database"],
    "machine learning": ["machine learning", "ml", "classification", "regression"],
    "deep learning": ["deep learning", "neural network", "tensorflow", "pytorch", "keras"],
    "nlp": ["nlp", "natural language", "llm", "transformer", "bert", "langchain"],
    "data analysis": ["data analysis", "analytics", "eda", "insight"],
    "data visualization": ["power bi", "tableau", "visualization", "dashboard", "matplotlib", "seaborn"],
    "cloud": ["aws", "gcp", "azure", "cloud", "s3", "ec2"],
    "docker": ["docker", "container", "kubernetes", "k8s"],
    "api development": ["api", "fastapi", "flask", "django", "rest", "graphql"],
    "web scraping": ["scraping", "selenium", "beautifulsoup", "crawl", "apify"],
    "git": ["git", "github", "version control"],
}

# Role-focused title mappings so synthetic skills are strongly aligned with the
# job title even when description text is sparse or noisy.
TITLE_ROLE_SKILLS = {
    "data scientist": [
        "python",
        "sql",
        "machine learning",
        "deep learning",
        "statistics",
        "data analysis",
        "data visualization",
    ],
    "data analyst": [
        "sql",
        "python",
        "excel",
        "data analysis",
        "data visualization",
        "power bi",
        "tableau",
    ],
    "machine learning engineer": [
        "python",
        "machine learning",
        "deep learning",
        "model deployment",
        "docker",
        "cloud",
        "sql",
    ],
    "ai engineer": [
        "python",
        "nlp",
        "llm",
        "langchain",
        "machine learning",
        "api development",
        "docker",
    ],
    "backend engineer": [
        "python",
        "api development",
        "sql",
        "docker",
        "git",
        "cloud",
    ],
    "software engineer": [
        "python",
        "git",
        "sql",
        "api development",
        "docker",
        "problem solving",
    ],
    "devops engineer": [
        "docker",
        "kubernetes",
        "cloud",
        "ci/cd",
        "linux",
        "git",
    ],
    "frontend developer": [
        "javascript",
        "html",
        "css",
        "react",
        "ui/ux",
        "git",
    ],
}


def _normalize_skills(skills: list) -> List[str]:
    """Normalize skill values to non-empty unique strings while preserving order."""
    normalized = []
    seen = set()
    for skill in skills:
        if skill is None:
            continue
        cleaned = str(skill).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def _build_synthetic_skills(raw_job: JobRaw) -> List[str]:
    """
    Build deterministic fallback skills from title/description text.

    This keeps pipelines moving even if the LLM is unavailable.
    """
    title = raw_job.title or ""
    description = raw_job.description or ""
    title_lc = title.lower()
    text_blob = f"{title} {description}".lower()

    generated = []

    # 1) Start with role signals from title for strong relevance.
    for role_phrase, role_skills in TITLE_ROLE_SKILLS.items():
        if role_phrase in title_lc:
            generated.extend(role_skills)

    # 2) Enrich using description/title keyword hits.
    for skill, keywords in SYNTHETIC_SKILL_KEYWORDS.items():
        if any(keyword in text_blob for keyword in keywords):
            generated.append(skill)

    # If very little signal was found, infer a few common baseline skills.
    if not generated:
        if re.search(r"data scientist|data analyst|ml engineer|machine learning engineer|ai engineer", text_blob):
            generated.extend(["python", "sql", "machine learning", "data analysis"])
        elif re.search(r"backend|software engineer|developer", text_blob):
            generated.extend(["python", "api development", "sql", "git"])
        elif re.search(r"devops", text_blob):
            generated.extend(["docker", "kubernetes", "cloud", "git"])
        else:
            generated.extend(["communication", "problem solving", "team collaboration"])

    return _normalize_skills(generated)[:SYNTHETIC_MAX_SKILLS]


def ingest_raw_jobs(db: Session, jobs_data: list) -> List[JobRaw]:
    """
    Insert raw Apify job records into `jobs_raw`.
    Deduplicates on `apify_job_id` — skips if already present.

    Returns list of newly inserted JobRaw objects.
    """
    inserted = []

    # Collect non-empty incoming IDs and prefetch existing IDs once.
    incoming_ids = {
        str(job.get("id", ""))
        for job in jobs_data
        if str(job.get("id", ""))
    }
    existing_ids = set()
    if incoming_ids:
        rows = db.execute(
            select(JobRaw.apify_job_id).where(JobRaw.apify_job_id.in_(incoming_ids))
        ).all()
        existing_ids = {row[0] for row in rows}

    # Track IDs seen in this in-memory batch to avoid duplicate inserts
    # before flush() hits the DB unique constraint.
    seen_in_batch = set(existing_ids)

    for job in jobs_data:
        apify_id = str(job.get("id", ""))

        # Skip duplicates already in DB or repeated inside input batch.
        if apify_id in seen_in_batch:
            logger.info(f"⏩ Skipping duplicate apify_job_id={apify_id}")
            continue

        raw_row = JobRaw(
            apify_job_id=apify_id,
            title=job.get("title"),
            company_name=job.get("companyName"),
            location=job.get("location"),
            experience_level=job.get("experienceLevel"),
            contract_type=job.get("contractType"),
            salary=job.get("salary"),
            description=job.get("description"),
            raw_data=job,
        )
        db.add(raw_row)
        seen_in_batch.add(apify_id)
        inserted.append(raw_row)

    db.flush()
    logger.info(f"✅ Inserted {len(inserted)} new rows into jobs_raw")
    return inserted


def extract_and_store_features(
    db: Session,
    raw_jobs: List[JobRaw],
    agents: Agents,
) -> List[JobFeatures]:
    """
    For each JobRaw, extract skills from description using the LLM,
    then insert an analytics-ready row into `job_features`.
    """
    features = []
    total = len(raw_jobs)

    for i, raw_job in enumerate(raw_jobs, 1):
        # Skip if features already extracted for this job
        existing = (
            db.query(JobFeatures)
            .filter(JobFeatures.job_raw_id == raw_job.id)
            .first()
        )
        if existing:
            continue

        skills = []

        # Run Ollama extraction with retries + timeout so a single slow/failing
        # call doesn't block or crash the entire batch run.
        if raw_job.description and not USE_SYNTHETIC_SKILLS_ONLY:
            for attempt in range(1, LLM_MAX_RETRIES + 1):
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            agents.job_summary_agent.invoke,
                            {"job_description": raw_job.description},
                        )
                        result = future.result(timeout=LLM_TIMEOUT_SECONDS)

                    skills = _normalize_skills(result.job_skills or [])
                    logger.info(
                        f"[{i}/{total}] 🔍 Extracted {len(skills)} skills from '{raw_job.title}' on attempt {attempt}/{LLM_MAX_RETRIES}"
                    )
                    break
                except TimeoutError:
                    logger.warning(
                        f"[{i}/{total}] ⏱️ Ollama timed out for job_raw_id={raw_job.id} on attempt {attempt}/{LLM_MAX_RETRIES} (>{LLM_TIMEOUT_SECONDS}s)."
                    )
                except Exception as e:
                    logger.warning(
                        f"[{i}/{total}] ⚠️ Skill extraction failed for job_raw_id={raw_job.id} on attempt {attempt}/{LLM_MAX_RETRIES}: {e}"
                    )

                # Simple backoff between retries
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(LLM_RETRY_SLEEP_SECONDS)

        if USE_SYNTHETIC_SKILLS_ONLY:
            logger.info(
                f"[{i}/{total}] 🧪 USE_SYNTHETIC_SKILLS_ONLY=true, skipping LLM and generating synthetic skills for job_raw_id={raw_job.id}."
            )

        if not skills:
            skills = _build_synthetic_skills(raw_job)
            logger.warning(
                f"[{i}/{total}] 🧪 Using {len(skills)} synthetic skills for job_raw_id={raw_job.id} after {LLM_MAX_RETRIES} failed attempts."
            )

        # Parse posted_date from raw_data
        posted_date = None
        raw_posted = raw_job.raw_data.get("postedDate")
        if raw_posted:
            try:
                posted_date = datetime.fromisoformat(raw_posted)
            except (ValueError, TypeError):
                pass

        feature_row = JobFeatures(
            job_raw_id=raw_job.id,
            title=raw_job.title,
            company_name=raw_job.company_name,
            location=raw_job.location,
            experience_level=raw_job.experience_level,
            contract_type=raw_job.contract_type,
            salary=raw_job.salary,
            job_url=raw_job.raw_data.get("url"),
            posted_date=posted_date,
            skills=skills,
        )
        db.add(feature_row)
        features.append(feature_row)

        if len(features) % 25 == 0:
            db.commit()
            logger.info(f"💾 Committed batch — {len(features)} features so far")

    db.flush()
    logger.info(f"✅ Inserted {len(features)} rows into job_features")
    return features
