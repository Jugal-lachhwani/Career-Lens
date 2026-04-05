"""
FastAPI REST API for Job Search Agent.

This module provides HTTP endpoints for running the job search workflow
via a web API, allowing integration with web frontends and other services.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
import tempfile
import os
from pathlib import Path
from sqlmodel import Session
from collections import Counter, defaultdict
from datetime import datetime

from src.graph import Workflow
from src.Database.database import init_db, engine
from src.models import JobListing, JobAnalysis, SearchHistory
from src.Postres.postres import SessionLocal as PostgresSessionLocal
from src.Postres.models import JobFeatures
from src.Database.db_operations import (
    save_workflow_results,
    get_all_jobs,
    get_job_with_analysis,
    get_search_history
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

# Initialize FastAPI app
app = FastAPI(
    title="Job Search Agent API",
    description="AI-powered job search and resume matching service",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global workflow instance (initialize once for efficiency)
workflow_instance = None

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


@app.post("/process-job-search", response_model=JobSearchResponse)
async def process_job_search(
    user_input: str = Form(..., description="Enter your job search query"),
    resume: UploadFile = File(...,description="Upload Resume PDF file(must be .pdf file)")
    # resume: UploadFile = File(..., description="Resume PDF file")
):
    """
    Process job search request with resume matching.
    
    Args:
        user_input: Natural language query (e.g., "Find Software Engineer jobs in India with 3 years experience")
        resume: PDF file of the resume
        
    Returns:
        JobSearchResponse containing job summaries, feedback, and resume analysis
        
    Raises:
        HTTPException: If processing fails
    """
    temp_resume_path = None
    
    try:
        logger.info(f"Received job search request: {user_input}")
        
        # Validate file type
        if not resume.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported for resume")
        
        # Save resume to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await resume.read()
            tmp.write(content)
            temp_resume_path = tmp.name
            logger.info(f"Resume saved to temporary path: {temp_resume_path}")
        
        # Update nodes to use the temporary resume path
        # This is a workaround - ideally nodes should accept resume_path in state
        original_resume_path = r"E:\\Genai_Projects\\Job_search_Agent\\Resume.pdf"
        
        # Initialize workflow state
        initial_state = {
            'user_input': user_input,
            'resume_path': temp_resume_path,
            'visited_ids': set(),
            'visited_ids_feedback': set()
        }
        
        # Get workflow and run it
        workflow = get_workflow()
        logger.info("Executing workflow...")
        final_state = workflow.app.invoke(initial_state)
        
        logger.info("Workflow completed successfully")
        
        # Save results to database
        try:
            with Session(engine) as db_session:
                save_workflow_results(
                    session=db_session,
                    user_query=user_input,
                    resume_name=resume.filename,
                    jobs=final_state.get('jobs', []),
                    job_summaries=final_state.get('job_summaries', []),
                    job_feedbacks=final_state.get('job_feedbacks', [])
                )
                logger.info("Results saved to database")
        except Exception as db_error:
            logger.error(f"Failed to save to database: {str(db_error)}", exc_info=True)
            # Continue execution even if database save fails
        
        # Extract and serialize results
        job_summaries = []
        for job in final_state.get('job_summaries', []):
            job_summaries.append(JobSummaryResponse(
                id=str(job.id),
                job_info=job.job_info,
                job_skills=job.job_skills
            ))
        
        job_feedbacks = []
        for feedback in final_state.get('job_feedbacks', []):
            job_feedbacks.append(JobFeedbackResponse(
                id=str(feedback.id),
                similarity=feedback.similarity,
                feedback=feedback.feedback
            ))
        
        resume_fields_data = final_state.get('resume_fields')
        resume_fields = ResumeFieldsResponse(
            skills=resume_fields_data.skills,
            profile=resume_fields_data.profile,
            Projects=resume_fields_data.Projects,
            Certifications=resume_fields_data.Certifications,
            Experience=resume_fields_data.Experience,
            Education=resume_fields_data.Education
        )
        
        return JobSearchResponse(
            success=True,
            job_summaries=job_summaries,
            job_feedbacks=job_feedbacks,
            resume_fields=resume_fields,
            message="Job search completed successfully"
        )
        
    except Exception as e:
        logger.error(f"Error processing job search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process job search: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if temp_resume_path and os.path.exists(temp_resume_path):
            try:
                os.unlink(temp_resume_path)
                logger.info("Temporary resume file deleted")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {str(e)}")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)