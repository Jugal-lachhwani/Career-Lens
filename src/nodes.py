"""
Workflow Nodes Module for Job Search Agent.

This module contains all the node functions that execute the various
stages of the job search and resume analysis workflow.
"""

import logging
from src.agents import Agents
from src.state import *
from src.tools.scraping_tools import *
from src.tools.google_sheets_writer import write_jobs_to_sheet

# Configure logging
logger = logging.getLogger(__name__)

class Nodes:
    """
    Collection of workflow node functions for the Job Search Agent.
    
    Each method represents a node in the LangGraph workflow that performs
    a specific task in the job search and resume analysis pipeline.
    
    Attributes:
        agents (Agents): Instance of the Agents class containing AI models.
    """
    
    def __init__(self):
        """
        Initialize the Nodes class with required agents.
        
        Creates an instance of the Agents class which contains all the
        AI models needed for job searching, resume analysis, and feedback.
        """
        logger.info("Initializing workflow nodes")
        self.agents = Agents()
        logger.debug("Agents initialized successfully")
        
    def job_searching_node(self, state: GraphState) -> GraphState:
        """
        Search for jobs based on user input and scrape job listings.
        
        This node:
        1. Takes user input from the state
        2. Uses the job input agent to structure the search query
        3. Calls the LinkedIn scraper with the structured query
        4. Returns a list of Job objects
        
        Args:
            state (GraphState): Current workflow state containing user_input.
            
        Returns:
            GraphState: Updated state with 'jobs' list populated.
            
        Raises:
            Exception: If job scraping fails.
        """
        logger.info("Starting job search node")
        user_input = state['user_input']
        logger.debug(f"User input: {user_input}")
        
        try:
            # Structure the user input into job search parameters
            logger.debug("Invoking job input agent")
            res = self.agents.job_input_agent.invoke({'user_prompt': user_input})
            
            # Convert to dictionary format for scraper
            job_info_dict = res.model_dump(
                mode="json",
                exclude=['days', 'jobType', 'experience_level'],
                exclude_none=True
            )
            logger.info(f"Job search parameters: {job_info_dict}")
            
            # Scrape jobs from LinkedIn
            logger.info("Initiating LinkedIn job scraping")
            jobs_data = job_scraping(job_info_dict)
            
            # Convert scraped items to Job objects
            l = []
            for job in jobs_data:
                l.append(Job(**job))

            logger.info(f"Successfully scraped {len(l)} jobs")
            return {'jobs': l}
            
        except Exception as e:
            logger.error(f"Error in job searching node: {str(e)}", exc_info=True)
            raise

    def resume_text_extractor(self, state: GraphState) -> GraphState:
        """
        Extract text content from a PDF resume.
        
        Reads the resume PDF file and extracts all text content for
        further processing and analysis.
        
        Args:
            state (GraphState): Current workflow state.
            
        Returns:
            GraphState: Updated state with 'resume_text' populated.
            
        Raises:
            FileNotFoundError: If resume PDF is not found.
            Exception: If PDF reading fails.
        """
        logger.info("Starting resume text extraction")
        
        try:
            from pypdf import PdfReader

            
            resume_path = state.get('resume_path',r"E:\Genai_Projects\Job_search_Agent\Resume.pdf")
            logger.debug(f"Reading resume from: {resume_path}")
            
            reader = PdfReader(resume_path)
            text = ""

            for page_num, page in enumerate(reader.pages):
                text += page.extract_text() + "\n"
                logger.debug(f"Extracted text from page {page_num + 1}")
            
            logger.info(f"Successfully extracted {len(text)} characters from resume")
            return {'resume_text': text}
            
        except FileNotFoundError:
            logger.error(f"Resume file not found at: {resume_path}")
            raise
        except Exception as e:
            logger.error(f"Error extracting resume text: {str(e)}", exc_info=True)
            raise
    
    def extract_fields_from_resume(self, state: GraphState) -> GraphState:
        """
        Extract structured fields from resume text using AI.
        
        Uses the resume agent to identify and extract key information
        such as skills, experience, education, etc. from the raw resume text.
        
        Args:
            state (GraphState): Current workflow state containing resume_text.
            
        Returns:
            GraphState: Updated state with 'resume_fields' populated.
            
        Raises:
            Exception: If field extraction fails.
        """
        logger.info("Starting resume field extraction")
        resume_text = state['resume_text']
        logger.debug(f"Processing resume text of length: {len(resume_text)}")
        
        try:
            logger.debug("Invoking resume agent")
            res = self.agents.resume_agent.invoke({'resume_text': resume_text})
            logger.info("Successfully extracted resume fields")
            logger.debug(f"Extracted fields: skills={len(res.skills)}, profile length={len(res.profile)}")
            
            return {'resume_fields': res}
            
        except Exception as e:
            logger.error(f"Error extracting resume fields: {str(e)}", exc_info=True)
            raise
    
    def extract_fields_from_job_desc(self, state: GraphState) -> GraphState:
        """
        Extract structured information from job descriptions.
        
        Processes each job in the state (skipping already visited ones) and
        extracts key information and required skills using AI.
        
        Args:
            state (GraphState): Current workflow state containing jobs list.
            
        Returns:
            GraphState: Updated state with 'job_summaries' and 'visited_ids'.
            
        Raises:
            Exception: If job description processing fails.
        """
        logger.info("Starting job description field extraction")
        visited_set = state['visited_ids']
        job_summary_model_list = []
        
        try:
            for job in state['jobs']:
                if job.id not in visited_set:
                    logger.debug(f"Processing job ID: {job.id} - {job.title}")
                    visited_set.add(job.id)
                    
                    # Extract job summary and skills
                    job_summary = self.agents.job_summary_agent.invoke({
                        'job_description': job.description
                    })
                    
                    job_summary_model = Job_Summary(
                        job_info=job_summary.job_info,
                        job_skills=job_summary.job_skills,
                        id=job.id
                    )
                    job_summary_model_list.append(job_summary_model)
                    logger.debug(f"Extracted {len(job_summary.job_skills)} skills from job {job.id}")
                else:
                    logger.debug(f"Skipping already visited job ID: {job.id}")
            
            logger.info(f"Successfully processed {len(job_summary_model_list)} job descriptions")
            return {'job_summaries': job_summary_model_list, 'visited_ids': visited_set}
            
        except Exception as e:
            logger.error(f"Error extracting job description fields: {str(e)}", exc_info=True)
            raise

    def Feedback_and_similarity(self, state: GraphState) -> GraphState:
        """
        Generate feedback and calculate similarity scores between resume and jobs.
        
        For each job, this node:
        1. Compares resume skills and profile with job requirements
        2. Calculates similarity score (0-100)
        3. Generates actionable feedback for improvement
        
        Args:
            state (GraphState): State containing resume_fields and job_summaries.
            
        Returns:
            GraphState: Updated state with 'job_feedbacks' and 'visited_ids_feedback'.
            
        Raises:
            Exception: If feedback generation fails.
        """
        logger.info("Starting feedback and similarity calculation")
        visited_set = state['visited_ids_feedback']
        job_feedback_model_list = []
        
        try:
            for job in state['job_summaries']:
                if job.id not in visited_set:
                    logger.debug(f"Generating feedback for job ID: {job.id}")
                    visited_set.add(job.id)
                    
                    resume_skills = state['resume_fields'].skills
                    resume_profile = state['resume_fields'].profile
                    job_skills = job.job_skills
                    job_info = job.job_info
                    
                    logger.debug(f"Comparing {len(resume_skills)} resume skills with {len(job_skills)} job skills")
                    
                    # Generate feedback and similarity score
                    job_feedback = self.agents.resume_feedback_agent.invoke({
                        'resume_skills': resume_skills,
                        'resume_profile': resume_profile,
                        'job_skills': job_skills,
                        'job_info': job_info
                    })
                    
                    job_feedback_model = Job_Feedback(
                        similarity=job_feedback.similarity,
                        feedback=job_feedback.feedback,
                        id=job.id
                    )
                    job_feedback_model_list.append(job_feedback_model)
                    logger.info(f"Job {job.id} similarity score: {job_feedback.similarity}")
                else:
                    logger.debug(f"Skipping already processed job ID: {job.id}")
            
            logger.info(f"Successfully generated feedback for {len(job_feedback_model_list)} jobs")
            return {'job_feedbacks': job_feedback_model_list, 'visited_ids_feedback': visited_set}
            
        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}", exc_info=True)
            raise

    def write_to_sheets(self, state: GraphState) -> GraphState:
        """
        Write all job data including summaries, similarity scores and feedback
        to Google Sheets.

        Args:
            state (GraphState): Final workflow state with jobs, summaries and feedbacks.

        Returns:
            GraphState: Unchanged state.
        """
        jobs = state.get('jobs', [])
        job_summaries = state.get('job_summaries', [])
        job_feedbacks = state.get('job_feedbacks', [])

        if jobs:
            logger.info("Writing %d jobs with summaries and feedback to Google Sheets", len(jobs))
            write_jobs_to_sheet(jobs, job_summaries, job_feedbacks)
        else:
            logger.info("No jobs to write to Google Sheets.")

        return {}
