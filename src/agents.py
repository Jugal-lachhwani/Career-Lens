"""
AI Agents Module for Job Search Application.

This module defines all the AI agents (LLM chains) used for various tasks
including job search parsing, resume analysis, and feedback generation.
"""

import logging
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from src.prompts import *
from src.structure_outputs import *
from src.llm_factory import get_json_llm
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class Agents:
    """
    Collection of AI agents for job search and resume analysis.
    
    This class initializes and manages various LLM-based agents that perform
    different tasks in the workflow:
    - Job search input parsing
    - Job description summarization
    - Resume field extraction
    - Resume-job matching and feedback
    
    Attributes:
        job_input_agent: Agent for parsing user job search queries.
        job_summary_agent: Agent for extracting key info from job descriptions.
        resume_agent: Agent for extracting structured fields from resumes.
        resume_feedback_agent: Agent for generating feedback and similarity scores.
    """
    
    def __init__(self):
        """
        Initialize all AI agents with their respective models and prompts.
        
        Sets up:
        - Ollama LLM (llama3.1:8b) for text generation
        - Prompt templates for each agent
        - Structured output schemas with PydanticOutputParser
        """
        logger.info("Initializing AI agents")
        
        # Initialize provider-configured LLM (Ollama or NVIDIA NIM)
        logger.debug("Loading provider-configured LLM for structured outputs")
        llm = get_json_llm(temperature=0.2)
        
        # Job Search Input Agent
        logger.debug("Setting up job searching agent")
        job_input_parser = PydanticOutputParser(pydantic_object=JobInfo)
        job_searching_prompt = PromptTemplate(
            template=JOB_SERCHING_PROMPT,
            input_variables=['user_prompt'],
            partial_variables={"format_instructions": job_input_parser.get_format_instructions()}
        )
        
        self.job_input_agent = (
            job_searching_prompt | llm | job_input_parser
        )
        logger.debug("Job searching agent initialized")
        
        # Job Description Summary Agent
        logger.debug("Setting up job summary agent")
        job_summary_parser = PydanticOutputParser(pydantic_object=Job_Summary)
        job_description_template = PromptTemplate(
            template=JOB_DESCRIPTION,
            input_variables=['job_description'],
            partial_variables={"format_instruction": job_summary_parser.get_format_instructions()}
        )
        
        self.job_summary_agent = (
            job_description_template | llm | job_summary_parser
        )
        logger.debug("Job summary agent initialized")
        
        # Resume Extraction Agent
        logger.debug("Setting up resume extraction agent")
        resume_parser = PydanticOutputParser(pydantic_object=Resume)
        resume_template = PromptTemplate(
            template=RESUME,
            input_variables=['resume_text'],
            partial_variables={"format_instructions": resume_parser.get_format_instructions()}
        )
        
        self.resume_agent = (
            resume_template | llm | resume_parser
        )
        logger.debug("Resume extraction agent initialized")
        
        # Resume Feedback Agent
        logger.debug("Setting up resume feedback agent")
        resume_feedback_parser = PydanticOutputParser(pydantic_object=SimilarityAndFeedback)
        resume_feedback_template = PromptTemplate(
            template=RESUME_FEEDBACK,
            input_variables=['resume_skills', 'resume_profile', 'job_skills', 'job_info'],
            partial_variables={"format_instructions": resume_feedback_parser.get_format_instructions()}
        )
        
        self.resume_feedback_agent = (
            resume_feedback_template | llm | resume_feedback_parser
        )
        logger.debug("Resume feedback agent initialized")
        
        logger.info("All AI agents initialized successfully")
        
        