"""
FastAPI REST API for Job Search Agent.

This module provides HTTP endpoints for running the job search workflow
via a web API, allowing integration with web frontends and other services.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
import tempfile
import os
from pathlib import Path
from sqlmodel import Session
from collections import Counter, defaultdict
from datetime import datetime

# --- Phase 4: Auth & CORS --------------------------------------------------
from src.auth import verify_api_key

# --- Rate Limiting (Step 3.3) -------------------------------------------
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# --- Celery task (Step 3.2) ------------------------------------------------
from src.tasks import run_job_search_task, celery_app as _celery_app

from src.graph import Workflow
from src.career_chatbot import CareerLensBot
from src.Database.database import init_db, engine
from src.models import JobListing, JobAnalysis, SearchHistory, ChatSession, ChatMessage
from src.Postres.postres import SessionLocal as PostgresSessionLocal
from src.Postres.models import JobFeatures
from src.Database.db_operations import (
    save_workflow_results,
    get_all_jobs,
    get_job_with_analysis,
    get_search_history,
    create_chat_session,
    get_chat_session,
    list_chat_sessions,
    save_chat_message,
    list_chat_messages,
)

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Configure logging with both console and file handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('logs/api.log', encoding='utf-8')  # File output
    ]
)
logger = logging.getLogger(__name__)

# Reduce noisy third-party logs for cleaner console output.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)

# Initialize FastAPI app
app = FastAPI(
    title="Job Search Agent API",
    description="AI-powered job search and resume matching service",
    version="1.0.0"
)

# --- Wire up rate limiter (Step 3.3) --------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Build CORS origin list from env (falls back to localhost for local dev)
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000",
)
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in _raw_origins.split(",") if o.strip()
]

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # Phase 4: no longer allow_origins=["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Global workflow instance (initialize once for efficiency)
workflow_instance = None
career_bot_instance = None

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    """Initialize database tables on application startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")


def get_db_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session


def get_postgres_session():
    """Dependency to get PostgreSQL session for analytics."""
    db = PostgresSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_workflow():
    """Get or create workflow instance."""
    global workflow_instance
    if workflow_instance is None:
        logger.info("Initializing workflow instance")
        workflow_instance = Workflow()
    return workflow_instance


def get_career_bot():
    """Get or create CareerLens chatbot instance."""
    global career_bot_instance
    if career_bot_instance is None:
        logger.info("Initializing CareerLens bot instance")
        career_bot_instance = CareerLensBot()
    return career_bot_instance


# Response Models
class JobSummaryResponse(BaseModel):
    """Job summary response model."""
    id: str
    job_info: str
    job_skills: List[str]


class JobFeedbackResponse(BaseModel):
    """Job feedback response model."""
    id: str
    similarity: int
    feedback: str


class ResumeFieldsResponse(BaseModel):
    """Resume fields response model."""
    skills: List[str]
    profile: str
    Projects: List[str]
    Certifications: List[str]
    Experience: List[str]
    Education: List[str]


class JobSearchResponse(BaseModel):
    """Complete job search response."""
    success: bool
    job_summaries: List[JobSummaryResponse]
    job_feedbacks: List[JobFeedbackResponse]
    resume_fields: ResumeFieldsResponse
    message: str


class CareerChatResponse(BaseModel):
    """CareerLens chatbot response model."""
    success: bool
    session_id: int
    answer: str
    tools_used: List[str]
    analytics_used: bool
    live_jobs_used: bool
    live_jobs_count: int
    top_skill_gaps: List[str]


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: str


ROLE_TITLE_HINTS = {
    "Data Scientist": ["data scientist"],
    "Data Analyst": ["data analyst", "business analyst", "bi analyst"],
    "Data Engineer": ["data engineer", "analytics engineer"],
    "ML Engineer": ["machine learning engineer", "ml engineer", "applied scientist"],
    "AI Engineer": ["ai engineer", "genai", "llm", "prompt engineer"],
    "Backend Engineer": ["backend", "back-end", "server-side"],
    "Frontend Engineer": ["frontend", "front-end", "ui engineer", "react developer"],
    "Full Stack Engineer": ["full stack", "full-stack", "fullstack"],
    "DevOps Engineer": ["devops", "site reliability", "sre", "platform engineer"],
    "Software Engineer": ["software engineer", "software developer", "application engineer"],
}


def _map_role_from_title(title: str | None) -> str:
    if not title:
        return "Other"

    title_lc = title.lower()
    for role, hints in ROLE_TITLE_HINTS.items():
        if any(hint in title_lc for hint in hints):
            return role
    return "Other"


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Job Search Agent API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "process": "/process-job-search",
            "task_status": "/tasks/{task_id}",
            "career_chat": "/career-chat",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Job Search Agent",
        "workflow_initialized": workflow_instance is not None
    }


# ---------------------------------------------------------------------------
# Step 3.2 — Async job-search endpoint (returns 202 immediately)
# ---------------------------------------------------------------------------

class TaskAcceptedResponse(BaseModel):
    """Returned immediately when a job-search task is accepted."""
    task_id: str
    status: str        # always "accepted"
    poll_url: str      # client should GET this URL to check progress


@app.post("/process-job-search", response_model=TaskAcceptedResponse, status_code=202)
@limiter.limit("5/minute")    # Step 3.3 — max 5 job searches per minute per IP
async def process_job_search(
    request: Request,           # Required by slowapi rate-limiter
    user_input: str = Form(..., description="Enter your job search query"),
    resume: UploadFile = File(..., description="Upload Resume PDF file (must be .pdf file)"),
    _key: str = Depends(verify_api_key),   # Phase 4 — API key required
):
    """
    Accepts a job search request and dispatches it to a Celery background worker.

    The endpoint returns **immediately** with HTTP 202 Accepted + a task_id.
    The actual workflow (Apify scraping + LLM calls, ~30-90 s) runs in the
    background.  Poll GET /tasks/{task_id} to check progress and retrieve
    the final result.

    Args:
        user_input: Natural language query
                    (e.g. "Find ML Engineer jobs in Bangalore with 2 years exp")
        resume:     PDF file of the candidate's resume.

    Returns:
        202 TaskAcceptedResponse  →  { task_id, status, poll_url }

    Raises:
        400: If the uploaded file is not a PDF.
        429: If the rate limit (5 requests/minute per IP) is exceeded.
        500: If task dispatch itself fails.
    """
    temp_resume_path = None

    try:
        logger.info("Received job search request (async): %r", user_input)

        # --- Validate file type -------------------------------------------
        if not resume.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported for resume."
            )

        # --- Persist resume to a temp file so the Celery worker can read it --
        # NOTE: The temp file is NOT deleted here — the Celery worker reads it
        # after this request returns.  The worker is responsible for cleanup.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await resume.read()
            tmp.write(content)
            temp_resume_path = tmp.name
            logger.info("Resume saved to temporary path: %s", temp_resume_path)

        # --- Dispatch to Celery (non-blocking) --------------------------------
        task = run_job_search_task.delay(user_input, temp_resume_path)
        logger.info("Job search task dispatched [task_id=%s]", task.id)

        return TaskAcceptedResponse(
            task_id=task.id,
            status="accepted",
            poll_url=f"/tasks/{task.id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error dispatching job search task: %s", str(e), exc_info=True)
        # Clean up temp file if dispatch failed
        if temp_resume_path and os.path.exists(temp_resume_path):
            try:
                os.unlink(temp_resume_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to dispatch job search task: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Step 3.2 — Task status / result polling endpoint
# ---------------------------------------------------------------------------

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Poll the status and result of a background job-search task.

    States:
        pending  — task is queued, not yet picked up by a worker
        running  — worker has started execution
        complete — workflow finished; `result` contains the full output
        failed   — workflow failed after retries; `error` contains the reason

    Args:
        task_id: The task ID returned by POST /process-job-search.

    Returns:
        JSON with `status` and optionally `result` or `error`.
    """
    result = _celery_app.AsyncResult(task_id)

    if result.state == "PENDING":
        return JSONResponse({"status": "pending", "task_id": task_id})

    elif result.state == "STARTED":
        return JSONResponse({"status": "running", "task_id": task_id})

    elif result.state == "SUCCESS":
        return JSONResponse({
            "status": "complete",
            "task_id": task_id,
            "result": result.result,   # dict serialised by _serialize_state()
        })

    elif result.state == "FAILURE":
        return JSONResponse(
            status_code=200,           # 200 so the client doesn't treat it as a transport error
            content={
                "status": "failed",
                "task_id": task_id,
                "error": str(result.info),
            },
        )

    else:
        # RETRY, REVOKED, etc.
        return JSONResponse({"status": result.state.lower(), "task_id": task_id})


@app.get("/jobs")
async def get_jobs(limit: int = 50, session: Session = Depends(get_db_session)):
    """
    Retrieve all saved job listings from database.
    
    Args:
        limit: Maximum number of jobs to return (default: 50)
        session: Database session dependency
        
    Returns:
        List of job listings with basic information
    """
    try:
        jobs = get_all_jobs(session, limit=limit)
        return {
            "success": True,
            "count": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "title": job.title,
                    "company_name": job.company_name,
                    "location": job.location,
                    "apply_url": job.apply_url,
                    "posted_date": job.posted_date,
                    "created_at": job.created_at.isoformat()
                }
                for job in jobs
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve jobs: {str(e)}")


@app.get("/jobs/{job_id}")
async def get_job_details(job_id: str, session: Session = Depends(get_db_session)):
    """
    Retrieve detailed information about a specific job including analysis.
    
    Args:
        job_id: Job ID
        session: Database session dependency
        
    Returns:
        Job details with analysis (summary, skills, similarity, feedback)
    """
    try:
        job = get_job_with_analysis(session, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        response = {
            "id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "location": job.location,
            "apply_url": job.apply_url,
            "description": job.description,
            "posted_date": job.posted_date,
            "created_at": job.created_at.isoformat(),
            "analysis": None
        }
        
        if job.analysis:
            response["analysis"] = {
                "summary": job.analysis.summary,
                "required_skills": job.analysis.skills,
                "similarity_score": job.analysis.similarity_score,
                "feedback": job.analysis.feedback
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve job: {str(e)}")


@app.get("/search-history")
async def get_history(limit: int = 20, session: Session = Depends(get_db_session)):
    """
    Retrieve search history.
    
    Args:
        limit: Maximum number of records to return (default: 20)
        session: Database session dependency
        
    Returns:
        List of past search queries with timestamps
    """
    try:
        history = get_search_history(session, limit=limit)
        return {
            "success": True,
            "count": len(history),
            "history": [
                {
                    "id": record.id,
                    "user_query": record.user_query,
                    "resume_name": record.resume_name,
                    "timestamp": record.timestamp.isoformat()
                }
                for record in history
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving search history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@app.get("/analytics/dashboard")
async def get_dashboard_analytics(session=Depends(get_postgres_session)):
    """
    Return aggregated dashboard analytics from PostgreSQL `job_features`.
    """
    try:
        rows = session.query(JobFeatures).all()

        if not rows:
            return {
                "success": True,
                "summary": {
                    "total_jobs": 0,
                    "unique_companies": 0,
                    "unique_locations": 0,
                    "unique_skills": 0,
                    "last_updated": None,
                },
                "top_skills": [],
                "role_counts": [],
                "engineering_role_counts": [],
                "top_locations": [],
                "top_companies": [],
                "timeline": [],
                "roles_by_location": [],
            }

        skill_counter = Counter()
        role_counter = Counter()
        engineering_role_counter = Counter()
        location_counter = Counter()
        company_counter = Counter()
        date_counter = Counter()
        location_role_counter = defaultdict(Counter)

        engineering_roles = {
            "Backend Engineer",
            "Frontend Engineer",
            "Full Stack Engineer",
            "DevOps Engineer",
            "Software Engineer",
            "Data Engineer",
            "ML Engineer",
            "AI Engineer",
        }

        for row in rows:
            role = _map_role_from_title(row.title)
            role_counter[role] += 1

            if role in engineering_roles:
                engineering_role_counter[role] += 1

            location = (row.location or "Unknown").strip() or "Unknown"
            company = (row.company_name or "Unknown").strip() or "Unknown"

            location_counter[location] += 1
            company_counter[company] += 1
            location_role_counter[location][role] += 1

            for skill in row.skills or []:
                cleaned = str(skill).strip()
                if cleaned:
                    skill_counter[cleaned] += 1

            if row.posted_date:
                day_key = row.posted_date.date().isoformat()
                date_counter[day_key] += 1

        top_locations = [
            {"location": location, "count": count}
            for location, count in location_counter.most_common(8)
        ]
        top_location_set = {item["location"] for item in top_locations}

        roles_by_location = []
        for location in top_location_set:
            for role, count in location_role_counter[location].most_common(5):
                roles_by_location.append(
                    {
                        "location": location,
                        "role": role,
                        "count": count,
                    }
                )

        return {
            "success": True,
            "summary": {
                "total_jobs": len(rows),
                "unique_companies": len(company_counter),
                "unique_locations": len(location_counter),
                "unique_skills": len(skill_counter),
                "last_updated": datetime.utcnow().isoformat(),
            },
            "top_skills": [
                {"skill": skill, "count": count}
                for skill, count in skill_counter.most_common(15)
            ],
            "role_counts": [
                {"role": role, "count": count}
                for role, count in role_counter.most_common(12)
            ],
            "engineering_role_counts": [
                {"role": role, "count": count}
                for role, count in engineering_role_counter.most_common(12)
            ],
            "top_locations": top_locations,
            "top_companies": [
                {"company": company, "count": count}
                for company, count in company_counter.most_common(12)
            ],
            "timeline": [
                {"date": date, "count": count}
                for date, count in sorted(date_counter.items())
            ],
            "roles_by_location": roles_by_location,
        }
    except Exception as e:
        logger.error(f"Error retrieving dashboard analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analytics: {str(e)}")


@app.post("/career-chat", response_model=CareerChatResponse)
@limiter.limit("20/minute")   # Step 3.3 — max 20 chat messages per minute per IP
async def career_chat(
    request: Request,           # Required by slowapi rate-limiter
    question: str = Form(..., description="User career question for CareerLens chatbot"),
    session_id: Optional[int] = Form(None, description="Optional chat session id for history"),
    resume: Optional[UploadFile] = File(None, description="Optional resume PDF for live resume-job matching"),
    live_job_query: Optional[str] = Form(None, description="Optional explicit query for live job extraction"),
    force_live_jobs: bool = Form(False, description="Force live job extraction and matching flow"),
    db_session: Session = Depends(get_db_session),
    postgres_session=Depends(get_postgres_session),
    _key: str = Depends(verify_api_key),   # Phase 4 — API key required
):
    """
    CareerLens GenAI chatbot endpoint.

    Features:
    - Uses analytics data for trend/skill guidance questions
    - Can trigger live job search + resume matching when required
    - Returns coaching-style guidance
    """
    temp_resume_path = None

    try:
        if resume is not None:
            if not resume.filename.endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Only PDF files are supported for resume")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                content = await resume.read()
                tmp.write(content)
                temp_resume_path = tmp.name
                logger.info("Career chat resume saved to temporary path: %s", temp_resume_path)

        workflow = get_workflow()
        career_bot = get_career_bot()

        # Create or load persistent chat session
        chat_session = None
        if session_id is not None:
            chat_session = get_chat_session(db_session, session_id)
            if chat_session is None:
                raise HTTPException(status_code=404, detail=f"Chat session {session_id} not found")
        else:
            title = (question[:60] + "...") if len(question) > 60 else question
            chat_session = create_chat_session(db_session, title=title)

        save_chat_message(db_session, chat_session.id, "user", question)

        recent_messages = list_chat_messages(db_session, session_id=chat_session.id, limit=20)
        history_payload = [
            {"role": m.role, "content": m.content}
            for m in recent_messages[:-1]  # exclude current user message; passed separately as `question`
        ]

        result = career_bot.answer(
            question=question,
            postgres_session=postgres_session,
            job_features_model=JobFeatures,
            workflow=workflow,
            chat_history=history_payload,
            resume_path=temp_resume_path,
            live_job_query=live_job_query,
            force_live_jobs=force_live_jobs,
        )

        save_chat_message(db_session, chat_session.id, "assistant", result.answer)

        return CareerChatResponse(
            success=True,
            session_id=chat_session.id,
            answer=result.answer,
            tools_used=result.tools_used,
            analytics_used=result.analytics_used,
            live_jobs_used=result.live_jobs_used,
            live_jobs_count=result.live_jobs_count,
            top_skill_gaps=result.top_skill_gaps,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in career chat endpoint: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process career chat: {str(e)}")
    finally:
        if temp_resume_path and os.path.exists(temp_resume_path):
            try:
                os.unlink(temp_resume_path)
            except Exception as cleanup_error:
                logger.warning("Failed to delete temporary file: %s", str(cleanup_error))


@app.get("/career-chat/sessions", response_model=List[ChatSessionResponse])
async def career_chat_sessions(
    limit: int = 30,
    db_session: Session = Depends(get_db_session),
):
    rows = list_chat_sessions(db_session, limit=limit)
    return [
        ChatSessionResponse(
            id=row.id,
            title=row.title,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
        for row in rows
    ]


@app.get("/career-chat/history/{session_id}", response_model=List[ChatMessageResponse])
async def career_chat_history(
    session_id: int,
    limit: int = 200,
    db_session: Session = Depends(get_db_session),
):
    chat_session = get_chat_session(db_session, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail=f"Chat session {session_id} not found")

    rows = list_chat_messages(db_session, session_id=session_id, limit=limit)
    return [
        ChatMessageResponse(
            id=row.id,
            session_id=row.session_id,
            role=row.role,
            content=row.content,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)