from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Text, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime, timezone

# 1. The Job Listing Table
class JobListing(SQLModel, table=True):
    id: str = Field(primary_key=True)  # The LinkedIn Job ID
    title: str
    company_name: str
    location: str
    apply_url: str
    description: str
    posted_date: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship to analysis
    analysis: Optional["JobAnalysis"] = Relationship(back_populates="job")

# 2. The Analysis Table
class JobAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="joblisting.id")

    summary: str
    # Native PostgreSQL array — no more JSON-string hacks
    skills: List[str] = Field(
        default=[],
        sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"),
    )
    similarity_score: int
    feedback: str

    # Relationship back to job
    job: Optional[JobListing] = Relationship(back_populates="analysis")

# 3. Search History Table
class SearchHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_query: str
    resume_name: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class ChatSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(default="New Chat")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id", index=True)
    role: str = Field(index=True)  # user | assistant
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)