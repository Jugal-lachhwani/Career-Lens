"""
Web Scraping Tools Module.

This module provides tools for scraping job listings from LinkedIn
using the Apify platform.
"""

import logging
import os
from apify_client import ApifyClient
import time
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_TOKEN" )
APIFY_ACTOR_NAME = os.getenv('APIFY_ACTOR_NAME' )

def linkedin_scrapper(actor_input: dict):
    """
    Scrape LinkedIn job listings using Apify Actor.
    
    This function uses the Apify platform to run a LinkedIn scraping actor
    that searches for jobs based on the provided input parameters.
    
    Args:
        actor_input (dict): Dictionary containing job search parameters.
            Expected keys include:
            - title: Job title to search for
            - location: Geographic location
            - datePosted: Date range filter
            - experienceLevel: Experience level filters
            - remote: Remote work type filters
            - limit: Maximum number of results
            
    Returns:
        ApifyDataset: Dataset object containing scraped job listings.
        Use dataset.iterate_items() to access individual job records.
        
    Raises:
        ValueError: If APIFY_TOKEN or APIFY_ACTOR_NAME not configured.
        ApifyClientError: If scraping fails or actor errors occur.
        
    Example:
        >>> job_params = {
        ...     'title': 'Data Scientist',
        ...     'location': 'India',
        ...     'limit': 10
        ... }
        >>> dataset = linkedin_scrapper(job_params)
        >>> for job in dataset.iterate_items():
        ...     print(job['title'])
    """
    
    # Validate environment variables
    if not APIFY_TOKEN:
        logger.error("APIFY_TOKEN environment variable not set")
        raise ValueError("APIFY_TOKEN environment variable is required")
    
    if not APIFY_ACTOR_NAME:
        logger.error("APIFY_ACTOR_NAME environment variable not set")
        raise ValueError("APIFY_ACTOR_NAME environment variable is required")
    
    logger.info("Initializing Apify client for LinkedIn scraping")
    logger.debug(f"Actor input parameters: {actor_input}")
    
    try:
        # Initialize Apify client
        apify_client = ApifyClient(APIFY_TOKEN)

        # Run the Actor with input parameters
        logger.info(f"Starting Apify Actor: {APIFY_ACTOR_NAME}")
        actor_name = APIFY_ACTOR_NAME
        actor_run = apify_client.actor(actor_name).start(run_input=actor_input)

        logger.info(f"🚀 Actor started successfully. Run ID: {actor_run['id']}")
        logger.info(f"💾 Monitor run at: https://console.apify.com/actors/runs/{actor_run['id']}")
        
        # Return dataset for iteration
        dataset = apify_client.dataset(actor_run["defaultDatasetId"])
        logger.info(f"Dataset ID: {actor_run['defaultDatasetId']}")
        
        return actor_run["defaultDatasetId"]
    
        
    except Exception as e:
        logger.error(f"Failed to scrape LinkedIn jobs: {str(e)}", exc_info=True)
        raise

# Helper: Poll dataset until items exist or timeout

def fetch_dataset_items_with_wait(
    dataset_id: str,
    token: str,
    wait_seconds: int = 20,
    poll_interval: int = 2
):
    """
    Poll Apify dataset until items are available or timeout is reached.
    """
    url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
    start_time = time.time()

    while True:
        response = requests.get(
            url,
            params={
                "token": token,
                "format": "json"
            }
        )
        response.raise_for_status()
        data = response.json()

        if data:
            return data

        elapsed = time.time() - start_time
        if elapsed >= wait_seconds:
            return []

        logger.info("Dataset empty, waiting...")
        time.sleep(poll_interval)

# Main Job Scrapping Function

def job_scraping(job_info_dict, wait_seconds=20):
    try:
        dataset_id = linkedin_scrapper(job_info_dict)
        logger.info(f"Dataset ID: {dataset_id}")
        logger.info(f"Apify Token: {APIFY_TOKEN}")

        # Step 5: Wait & fetch dataset items
        logger.info(f"\n--- Step 5: Fetching Dataset Items (wait max {wait_seconds}s) ---")
        jobs_data = fetch_dataset_items_with_wait(
            dataset_id=dataset_id,
            token=APIFY_TOKEN,
            wait_seconds=wait_seconds,
            poll_interval=2
        )

        if not jobs_data:
            logger.warning("⚠️ No jobs fetched after 10 seconds")
        else:
            logger.info(f"✅ Fetched {len(jobs_data)} jobs")

        return jobs_data

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        raise
