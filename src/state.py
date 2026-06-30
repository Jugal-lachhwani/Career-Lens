"""
State Management Module for Job Search Agent.

This module defines all state models and data structures used throughout
the job search and resume analysis workflow.
"""

from pydantic import BaseModel, field_validator
from typing import List, TypedDict, Set, Annotated
import operator


class Job(BaseModel):
    """
    Complete job listing information scraped from LinkedIn.
    
    Attributes:
        id (str): Unique job identifier.
        url (str): Direct URL to the job posting.
        title (str): Job title/position name.
        location (str): Job location (city, state, country).
        companyName (str): Name of the hiring company.
        companyUrl (str): LinkedIn URL of the company.
        recruiterName (str): Name of the recruiter (if available).
        recruiterUrl (str): LinkedIn URL of the recruiter.
        experienceLevel (str): Required experience level (Entry, Mid, Senior, etc.).
        contractType (str): Type of employment (Full-time, Part-time, Contract, etc.).
        workType (str): Nature of work/department.
        sector (str): Industry sector of the company.
        salary (str): Salary information (if provided).
        applyType (str): Application method (EASY_APPLY, EXTERNAL, etc.).
        applyUrl (str): URL to apply for the job.
        postedTimeAgo (str): Human-readable time since posting.
        postedDate (str): ISO format date of posting.
        applicationsCount (str): Number of applicants.
        description (str): Full job description text.
    """
    id: str
    url: str
    title: str
    location: str
    companyName: str 
    companyUrl: str
    recruiterName: str
    recruiterUrl: str
    experienceLevel: str
    contractType: str
    workType: str
    sector: str
    salary: str
    applyType: str
    applyUrl: str 
    postedTimeAgo: str  
    postedDate: str
    applicationsCount: str
    description: str

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_string(cls, value):
        if value is None:
            raise ValueError("Job id cannot be None")
        return str(value)


class Job_Info_state(BaseModel):
    """
    Structured job search parameters derived from user input.
    
    This model represents the parsed and structured version of user's
    job search request, ready to be used with the LinkedIn API.
    
    Attributes:
        title (str | None): Job title to search for.
        location (str | None): Location filter for jobs.
        datePosted (str | None): Date range filter for job postings.
        companyName (List[str] | None): Preferred companies to search within.
        companyId (List[str] | None): Company IDs to filter by.
        skipJobId (List[str] | None): Job IDs to exclude from results.
        remote (List[str] | None): Remote work preferences (remote, hybrid, onsite).
        experienceLevel (List[str] | None): Experience level filters.
        contractType (List[str] | None): Contract type filters.
        limit (int | None): Maximum number of jobs to retrieve.
    """
    title: str | None
    location: str | None
    datePosted: str | None
    companyName: List[str] | None
    companyId: List[str] | None
    skipJobId: List[str] | None
    remote: List[str] | None
    experienceLevel: List[str] | None
    contractType: List[str] | None
    limit: int | None


class Job_Summary(BaseModel):
    """
    Summarized and extracted information from a job description.
    
    Attributes:
        job_info (str): Concise summary of the job role and responsibilities.
        job_skills (List[str]): List of required skills extracted from description.
        id (str): Unique identifier linking to the original Job.
    """
    job_info: str
    job_skills: List[str]
    id: str


class Job_Feedback(BaseModel):
    """
    Feedback and similarity analysis between resume and job posting.
    
    Attributes:
        similarity (int): Similarity score (0-100) between resume and job.
        job_id (str): Job ID this feedback relates to.
        feedback (str): Detailed feedback on what's missing or needs improvement.
    """
    similarity: int
    id: str
    feedback: str


class Resume_Fields(BaseModel):
    """
    Structured fields extracted from resume text.
    
    Attributes:
        skills (List[str]): Technical and domain-specific skills.
        profile (str): Professional summary/profile section.
        Projects (List[str]): List of projects mentioned in resume.
        Certifications (List[str]): Professional certifications.
        Experience (List[str]): Work experience entries.
        Education (List[str]): Educational qualifications.
    """
    skills: List[str]
    profile: str
    Projects : List[str]
    Certifications : List[str]
    Experience : List[str]   
    Education : List[str]


class GraphState(TypedDict):
    """
    Main workflow state that flows through all nodes in the LangGraph.
    
    This TypedDict defines the complete state structure that gets passed
    between nodes in the workflow. Some fields use Annotated with operators
    to specify how they should be combined when multiple nodes write to them.
    
    Attributes:
        user_input (str): Original user query/request for job search.
        job_info (Job_Info_state): Structured job search parameters.
        resume_text (str): Raw text extracted from resume PDF.
        jobs (List[Job]): List of scraped job postings.
        visited_ids (Set[str]): Set of job IDs already processed for summaries.
        job_summaries (Annotated[List[Job_Summary], operator.add]): 
            Accumulated list of job summaries (nodes can append to it).
        resume_fields (Resume_Fields): Structured resume information.
        job_feedbacks (Annotated[List[Job_Feedback], operator.add]): 
            Accumulated feedback and similarity scores for jobs.
        visited_ids_feedback (Set[str]): Set of job IDs already processed for feedback.
    """
    user_input: str
    resume_path: str
    job_info: Job_Info_state
    resume_text: str
    jobs: List[Job]
    visited_ids: Set[str]
    job_summaries: Annotated[List[Job_Summary], operator.add]
    resume_fields: Resume_Fields
    job_feedbacks: Annotated[List[Job_Feedback], operator.add]
    visited_ids_feedback: Set[str]