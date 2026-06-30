"""
Quick test to verify database integration works.
"""

from sqlmodel import Session
from src.Database.database import init_db, engine
from src.models import JobListing, JobAnalysis, SearchHistory
from datetime import datetime

def test_database():
    """Test database initialization and basic operations."""
    
    print("1. Initializing database...")
    init_db()
    print("✓ Database initialized")
    
    print("\n2. Testing JobListing creation...")
    with Session(engine) as session:
        # Create a test job
        test_job = JobListing(
            id="test_job_123",
            title="Test Software Engineer",
            company_name="Test Company",
            location="Test Location",
            apply_url="https://test.com/apply",
            description="Test job description",
            posted_date="2026-01-18"
        )
        session.add(test_job)
        session.commit()
        print("✓ JobListing created")
        
        print("\n3. Testing JobAnalysis creation...")
        # Create test analysis
        test_analysis = JobAnalysis(
            job_id="test_job_123",
            summary="This is a test job summary",
            similarity_score=85,
            feedback="Good match for your skills"
        )
        test_analysis.skills = ["Python", "FastAPI", "SQLModel"]
        session.add(test_analysis)
        session.commit()
        print("✓ JobAnalysis created")
        
        print("\n4. Testing SearchHistory creation...")
        # Create test search history
        test_search = SearchHistory(
            user_query="Find software engineer jobs",
            resume_name="test_resume.pdf"
        )
        session.add(test_search)
        session.commit()
        print("✓ SearchHistory created")
        
        print("\n5. Testing data retrieval...")
        # Retrieve the job with analysis
        job = session.get(JobListing, "test_job_123")
        print(f"✓ Retrieved job: {job.title}")
        print(f"  Company: {job.company_name}")
        print(f"  Analysis: {job.analysis.summary if job.analysis else 'None'}")
        print(f"  Skills: {job.analysis.skills if job.analysis else []}")
        print(f"  Similarity: {job.analysis.similarity_score if job.analysis else 'N/A'}")
    
    print("\n✅ All database tests passed!")
    print("\nDatabase file created at: ./job_agent.db")

if __name__ == "__main__":
    test_database()
