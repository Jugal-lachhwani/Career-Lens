"""
Prompt Templates for AI Agents.

This module contains all the prompt templates used by various AI agents
in the job search and resume analysis workflow.
"""

# Job Search Prompt Template
JOB_SERCHING_PROMPT = """
You are a job-search helper agent.

Extract structured information from the user query.

{format_instructions}

User query:
{user_prompt}
"""


# Resume Analysis Prompt Template
RESUME = """
You are an information extraction agent.

Extract the following fields from the resume text and return ONLY a JSON object
that matches the schema exactly.

{format_instructions}

Resume text:
{resume_text}
"""


# Resume Feedback and Similarity Prompt Template
RESUME_FEEDBACK = """
You are a resume improvement agent.

Analyze how well the resume matches the given job.

Tasks:
1. Identify missing skills, keywords, or projects.
2. Provide clear and actionable feedback.
3. Give a similarity score between 0 and 100.

Follow the format instructions STRICTLY.
Return only the structured output.

{format_instructions}

Resume skills:
{resume_skills}

Resume profile:
{resume_profile}

Job information:
{job_info}

Job required skills:
{job_skills}
"""

JOB_DESCRIPTION = """You are an expert technical recruiter analyzing job descriptions.

Task: Extract ALL technical skills, programming languages, frameworks, arrays, and tools mentioned in the job description below.
Even if they are only briefly mentioned or implied, you MUST add them to the skills list! If none are found, list ['None'].

Submit your output strictly in the requested format.
{format_instruction} 

Job Description text: 
{job_description}"""