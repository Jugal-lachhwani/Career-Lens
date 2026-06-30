"""
Job Search Agent Workflow Module.

This module defines the main workflow for the Job Search Agent application.
It orchestrates parallel processing of job searching and resume analysis,
culminating in feedback generation and similarity scoring.
"""

import logging
from langgraph.graph import END, StateGraph, START
from src.state import GraphState
from src.nodes import Nodes

# Configure logging
logger = logging.getLogger(__name__)


class Workflow():
    """
    Main workflow orchestrator for the Job Search Agent.
    
    This class builds and compiles a LangGraph workflow that:
    1. Executes two parallel branches:
       - Branch 1: Searches jobs and extracts fields from job descriptions
       - Branch 2: Extracts resume text and extracts fields from resume
    2. Converges both branches for feedback and similarity analysis
    
    The workflow uses LangGraph's fan-in pattern to ensure both parallel
    paths complete before executing the final feedback node.
    
    Attributes:
        app: The compiled LangGraph application ready for execution.
    """
    
    def __init__(self):
        """
        Initialize the workflow by creating the state graph and adding nodes/edges.
        
        Creates a parallel workflow structure with:
        - Job searching and description extraction branch
        - Resume text extraction and field extraction branch
        - Convergence node for feedback and similarity scoring
        """
        logger.info("Initializing Job Search Agent Workflow")
        
        workflow = StateGraph(GraphState)
        nodes = Nodes()
        
        logger.debug("Adding workflow nodes")
        # Add all nodes
        workflow.add_node("job_searching_node", nodes.job_searching_node)
        workflow.add_node("resume_text_extractor", nodes.resume_text_extractor)
        workflow.add_node("extract_fields_from_resume", nodes.extract_fields_from_resume)
        workflow.add_node("extract_fields_from_job_desc", nodes.extract_fields_from_job_desc)
        workflow.add_node("Feedback_and_similarity", nodes.Feedback_and_similarity)
        
        logger.debug("Configuring workflow edges")
        # Branch 1: Job Description Path
        workflow.add_edge(START, "job_searching_node")
        workflow.add_edge("job_searching_node", "extract_fields_from_job_desc")
        
        # Branch 2: Resume Path
        workflow.add_edge(START, "resume_text_extractor")
        workflow.add_edge("resume_text_extractor", "extract_fields_from_resume")
        
        # Both branches converge to Feedback node (LangGraph waits for both)
        workflow.add_edge("extract_fields_from_job_desc", "Feedback_and_similarity")
        workflow.add_edge("extract_fields_from_resume", "Feedback_and_similarity")
        
        # End workflow
        workflow.add_edge("Feedback_and_similarity", END)
        
        logger.info("Compiling workflow graph")
        self.app = workflow.compile()
        logger.info("Workflow initialization complete")
        
        
        