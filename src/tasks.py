"""
Celery task definitions for CareerLens background job processing.

This module moves the long-running LangGraph workflow (30-90 seconds due to
Apify scraping + LLM calls) out of the HTTP request/response cycle so that:
  - POST /process-job-search  →  returns 202 + task_id immediately
  - GET  /tasks/{task_id}     →  client polls for progress / result

Starting a Celery worker (separate terminal):
    celery -A src.tasks worker --loglevel=info --concurrency=4

On Windows (no fork()), add --pool=solo for debugging:
    celery -A src.tasks worker --loglevel=info --pool=solo

Redis must be running and REDIS_URL set (defaults to redis://localhost:6379/0).
Install Redis on Windows via:
    - WSL2:  sudo apt install redis-server && redis-server
    - Docker: docker run -p 6379:6379 redis:7-alpine
"""

import os
import logging
from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# ---------------------------------------------------------------------------
# Celery application — broker & result backend both point to Redis
# ---------------------------------------------------------------------------
celery_app = Celery(
    "careerlens",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Task tracking & timeouts
    task_track_started=True,     # Enables the STARTED state (visible via GET /tasks)
    task_time_limit=300,         # Hard kill after 5 min  (workflow should finish by then)
    task_soft_time_limit=240,    # Raise SoftTimeLimitExceeded at 4 min for graceful cleanup

    # Worker concurrency (overridable via CLI --concurrency flag)
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "4")),

    # Result expiry — keep results in Redis for 24 hours
    result_expires=86400,

    # Retry configuration
    task_acks_late=True,          # Acknowledge task only after completion (safe retries)
    task_reject_on_worker_lost=True,

    # Windows compatibility — use threads instead of fork
    # Switch to "prefork" on Linux for true multi-process parallelism
    worker_pool=os.getenv("CELERY_POOL", "solo"),
)


# ---------------------------------------------------------------------------
# Helper: serialize the final LangGraph state into JSON-safe primitives
# ---------------------------------------------------------------------------
def _serialize_state(final_state: dict) -> dict:
    """
    Convert LangGraph final state to JSON-serializable dict.

    The state contains Pydantic model instances (job_summaries, job_feedbacks,
    resume_fields) that must be converted to plain dicts before Celery can
    store them in Redis.
    """
    def _obj_to_dict(obj):
        if hasattr(obj, "model_dump"):          # Pydantic v2
            return obj.model_dump()
        if hasattr(obj, "dict"):                # Pydantic v1
            return obj.dict()
        if isinstance(obj, set):
            return list(obj)                    # sets are not JSON-serializable
        return obj

    job_summaries = [
        _obj_to_dict(j) for j in final_state.get("job_summaries", [])
    ]
    job_feedbacks = [
        _obj_to_dict(f) for f in final_state.get("job_feedbacks", [])
    ]
    resume_fields_raw = final_state.get("resume_fields")
    resume_fields = _obj_to_dict(resume_fields_raw) if resume_fields_raw else {}

    return {
        "job_summaries": job_summaries,
        "job_feedbacks": job_feedbacks,
        "resume_fields": resume_fields,
    }


# ---------------------------------------------------------------------------
# Background task — executes the full LangGraph workflow
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    max_retries=2,
    name="src.tasks.run_job_search_task",
)
def run_job_search_task(self, user_input: str, resume_path: str):
    """
    Execute the CareerLens LangGraph workflow as a Celery background task.

    Args:
        user_input:   Natural-language job search query from the user.
        resume_path:  Path to the temporary PDF file saved by the API endpoint.

    Returns:
        dict: { "status": "complete", "data": { job_summaries, job_feedbacks,
               resume_fields } }

    Raises:
        Celery retries the task (up to max_retries=2) on any unhandled
        exception, with a 10-second delay between retries.
    """
    logger.info(
        "Starting job search task [task_id=%s]  user_input=%r  resume=%s",
        self.request.id,
        user_input,
        resume_path,
    )

    try:
        # Import inside the task to avoid circular imports and to let Celery
        # workers initialise cleanly before heavy imports are resolved.
        from src.graph import Workflow

        # Each task creates its own Workflow instance so there is no shared
        # mutable state between concurrent workers.
        workflow = Workflow()

        initial_state = {
            "user_input": user_input,
            "resume_path": resume_path,
            "visited_ids": set(),
            "visited_ids_feedback": set(),
        }

        logger.info("Invoking LangGraph workflow [task_id=%s]", self.request.id)
        final_state = workflow.app.invoke(initial_state)
        logger.info("Workflow completed [task_id=%s]", self.request.id)

        serialized = _serialize_state(final_state)
        return {"status": "complete", "data": serialized}

    except Exception as exc:
        logger.error(
            "Job search task failed [task_id=%s]: %s",
            self.request.id,
            str(exc),
            exc_info=True,
        )
        # Retry with a 10-second back-off; raises MaxRetriesExceededError after 2 retries
        raise self.retry(exc=exc, countdown=10)
