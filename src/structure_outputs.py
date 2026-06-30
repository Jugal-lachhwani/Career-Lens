"""
Structured Output Models for AI Agents.

This module defines Pydantic models that structure the outputs from
various AI agents, ensuring type safety and data validation.
"""

from pydantic import BaseModel, Field, computed_field, field_validator
from typing import List
from enum import Enum


class JobType(str, Enum):
    """
    Enumeration of job location/work arrangement types.
    
    Attributes:
        REMOTE: Fully remote work.
        HYBRID: Mix of remote and office work.
        ONSITE: Work from office only.
    """
    REMOTE = 'remote'
    HYBRID = 'hybrid'
    ONSITE = 'onsite'


class ExperienceLevel(str, Enum):
    """
    Enumeration of professional experience levels.
    
    Attributes:
        Internship: Internship positions.
        Entry_level: Entry-level positions (0-2 years).
        Associate: Associate level (2-5 years).
        Mid_Senior_level: Mid to senior level (5-10 years).
        Director: Director level positions.
        Executive: Executive/C-level positions.
    """
    Internship = "Internship"
    Entry_level = "Entry_level"
    Associate = "Associate"
    Mid_Senior_level = "Mid_Senior_level"
    Director = "Director"
    Executive = "Executive"


class JobInfo(BaseModel):
    """
    Structured job search parameters extracted from user input.
    
    This model is used to parse natural language job search queries into
    structured parameters that can be used with job search APIs.
    
    Attributes:
        title: Primary job title or role to search for.
        location: Country where jobs should be searched.
        days: Number of days to look back for job postings.
        companyName: Preferred companies, ordered by priority.
        companyId: Company IDs to filter by, ordered by priority.
        skipJobId: Job IDs to exclude from results.
        jobType: Preferred work arrangements (remote, hybrid, onsite).
        experience_level: Preferred experience levels, ordered by priority.
        limit: Maximum number of jobs to retrieve (capped at 3).
    """
    title: str | None = Field(
        default=None,
        description="Primary job title or role to search for.This represents the main occupation or position of interest.",
        examples=['AI engineer', 'Data Scientist', 'SQL', 'Java', 'Software Engineer']
    )
    location: str | None = Field(
        default=None,
        description="The name of the country where job needs to be find, If any city name is entered then think of the contry in which the city exist",
        examples=['India', 'America']
    )
    days: int = Field(
        default=7,
        description="Job posted within the last days",
        examples=[1, 3, 7, 14]
    )
    companyName: List[str] | None = Field(
        default=None,
        description="The List of companies which needs to consider first or which is only needs to considered, ordered by priority",
        examples=['Google', 'Microsoft']
    )
    companyId: List[str] | None = Field(
        default=None,
        description="The List of Ids of the companies which needs to consider first or which is only needs to considered, ordered by priority",
        examples=['21345', '5567483']
    )
    skipJobId: List[str] | None = Field(
        default=None,
        description="The List of Ids of the companies which needs to  be skiped or not considered",
        examples=['21345', '5567483']
    )
    jobType: List[JobType] | None = Field(
        default=None,
        description="This is the list of type of job the user preferred, ordered by priority",
        examples=[['remote', 'hybrid'], ['onsite']]
    )
    experience_level: List[ExperienceLevel] | None = Field(
        default=None,
        description="Preferred experience levels for the job, ordered by priority (from most to least preferred)."
    )
    limit: int | None = Field(
        default=3,
        description="The number of jobs the user wants to find even if the user will say a big number limit it up to 3",
        le=3,
        ge=1,
        examples=[3, 1, 2]
    )

    @field_validator("days", mode="before")
    @classmethod
    def default_days_when_null(cls, value):
        # LLM output occasionally returns null; default to 7 days instead of failing later.
        return 7 if value is None else value
    
    @computed_field
    @property
    def datePosted(self) -> str:
        """
        Convert days to LinkedIn API date format.
        
        Returns:
            str: Date filter in format 'r{seconds}' for LinkedIn API.
        """
        return "r" + str(int(self.days) * 86400)

    @computed_field
    @property
    def remote(self) -> List[int] | None:
        """
        Convert JobType enum to LinkedIn API remote filter codes.
        
        Returns:
            List[int] | None: List of remote type codes (1=onsite, 2=remote, 3=hybrid).
        """
        if not self.jobType:
            return None

        mapping = {
            JobType.ONSITE: '1',
            JobType.REMOTE: '2',
            JobType.HYBRID: '3',
        }

        return [mapping[jt] for jt in self.jobType]
    
    @computed_field
    @property
    def experienceLevel(self) -> List[str] | None:
        """
        Convert ExperienceLevel enum to LinkedIn API experience filter codes.
        
        Returns:
            List[str] | None: List of experience level codes (1-6).
        """
        if not self.experience_level:
            return None

        mapping = {
            ExperienceLevel.Internship: "1",
            ExperienceLevel.Entry_level: "2",
            ExperienceLevel.Associate: "3",
            ExperienceLevel.Mid_Senior_level: "4",
            ExperienceLevel.Director: "5",
            ExperienceLevel.Executive: "6",
        }

        return [mapping[ctype] for ctype in self.experience_level]  


class Resume(BaseModel):
    """
    Structured fields extracted from a resume.
    
    Attributes:
        skills: Technical and domain-specific skills (not soft skills).
        profile: Brief professional summary about the candidate.
        Projects: List of projects mentioned in the resume.
        Certifications: Professional certifications held.
        Experience: Work experience details.
        Education: Educational qualifications.
    """
    skills: List[str] = Field(
        default=['No skills'],
        description="The main programing and technikal skills focus more on the domain specific skills rather than soft skills"
    )
    profile: str = Field(
        default='No profile',
        description="The brief info about the user found in the resume text"
    )
    Projects: List[str] = Field(
        default=['No Projects'],
        description="The Projects that are built by the user found in the resume"
    )
    Certifications: List[str] = Field(
        default=['No Certifications'],
        description='THe certifications of the user in the resume'
    )
    Experience: List[str] = Field(
        default=['No Experience'],
        description="The Experience of the user mentioned in the resume"
    )
    Education: List[str] = Field(
        default='[No Education]',
        description='The education oof the yser found in the resume'
    )


class SimilarityAndFeedback(BaseModel):
    similarity: int = Field(
        ...,
        ge=0,
        le=100,
        description="Similarity score between 0 and 100 indicating how well the job matches the resume."
    )
    feedback: str = Field(
        default="No feedback",
        description="Actionable feedback describing missing skills, keywords, or projects needed to improve the resume for this job."
    )


class Job_Summary(BaseModel):
    """
    Extracted summary and key information from job description.
    
    Attributes:
        id: Unique job identifier.
        job_skills: List of required skills mentioned in the job.
        job_info: 3-line summary of the job role.
    """
    id: str
    job_skills: List[str] = Field(
        ...,
        description='Extract the skills that are mentioned in the Job description'
    )
    job_info: str = Field(
        ...,
        description="Summary of the job in 3 lines"
    )