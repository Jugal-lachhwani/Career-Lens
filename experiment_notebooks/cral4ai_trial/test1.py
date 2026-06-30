# Import required libraries
import asyncio
import nest_asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.chunking_strategy import RegexChunking
import json
import time
import logging
from typing import Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Allow nested event loops (important for Jupyter)
nest_asyncio.apply()
print("✅ Libraries imported successfully")


async def scrape_linkedin_job(job_url: str, retry_count: int = 3) -> Optional[Dict]:
    """
    Scrape LinkedIn job posting with improved error handling and data extraction.
    
    Args:
        job_url: LinkedIn job URL
        retry_count: Number of retries on failure
        
    Returns:
        Dictionary with job information or None if failed
    """
    
    # Define extraction prompt for better data parsing
    extraction_prompt = """
    Extract the following information from the LinkedIn job posting:
    1. Job Title
    2. Company Name
    3. Location
    4. Job Type (Full-time, Part-time, Contract, etc.)
    5. Experience Level
    6. Salary (if available)
    7. Key Responsibilities (bullet points)
    8. Required Skills
    9. About the Company
    10. Full job description
    
    Format the output as a structured JSON object.
    """
    
    for attempt in range(retry_count):
        try:
            logger.info(f"Scraping attempt {attempt + 1}/{retry_count} for {job_url}")
            
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=job_url,
                    bypass_cache=True,
                    word_count_threshold=10,
                    wait_for="css:.jobs-details",
                    wait_timeout=15000,
                    js_code=[
                        # Scroll to load all content
                        "window.scrollTo(0, document.body.scrollHeight);",
                        "await new Promise(r => setTimeout(r, 1000));",
                        # Scroll back to top to ensure full load
                        "window.scrollTo(0, 0);",
                        "await new Promise(r => setTimeout(r, 500));"
                    ],
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                
                if not result.success:
                    logger.warning(f"Crawl failed: {result.error_message}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Failed after {retry_count} attempts")
                        return None
                
                # Validate content
                if not result.markdown or len(result.markdown.strip()) < 100:
                    logger.warning("Content too short, retrying...")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                
                logger.info("✅ Successfully scraped job page!")
                
                # Extract structured data
                job_data = {
                    "metadata": {
                        "url": job_url,
                        "scraped_at": datetime.now().isoformat(),
                        "content_length": len(result.markdown),
                        "success": True
                    },
                    "job_description": result.markdown,
                    "raw_html": result.html if result.html else None,
                    "extracted_data": extract_job_info(result.markdown)
                }
                
                logger.info(f"Extracted {len(job_data['extracted_data'].get('responsibilities', []))} responsibilities")
                return job_data
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout on attempt {attempt + 1}")
            if attempt < retry_count - 1:
                await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < retry_count - 1:
                await asyncio.sleep(2 ** attempt)
    
    logger.error("All scraping attempts failed")
    return None


def extract_job_info(markdown_content: str) -> Dict:
    """
    Extract structured job information from markdown content.
    
    Args:
        markdown_content: Markdown content from scraped page
        
    Returns:
        Dictionary with extracted job information
    """
    
    lines = markdown_content.split('\n')
    job_info = {
        "title": None,
        "company": None,
        "location": None,
        "job_type": None,
        "description": "",
        "responsibilities": [],
        "requirements": [],
        "benefits": []
    }
    
    # Try to extract basic info from headers
    for i, line in enumerate(lines[:30]):  # Check first 30 lines
        line_clean = line.strip()
        
        # Title extraction
        if line_clean.startswith('#') and job_info["title"] is None:
            job_info["title"] = line_clean.replace('#', '').strip()
        
        # Location and type extraction
        if '📍' in line or 'Location:' in line.lower():
            job_info["location"] = line_clean.replace('📍', '').strip()
        
        if 'Full-time' in line or 'Part-time' in line or 'Contract' in line:
            job_info["job_type"] = line_clean.strip()
    
    # Extract responsibilities and requirements
    current_section = None
    for line in lines:
        line_clean = line.strip()
        
        if any(x in line.lower() for x in ['responsib', 'you will', 'you\'ll']):
            current_section = 'responsibilities'
        elif any(x in line.lower() for x in ['require', 'qualif', 'must have', 'skills']):
            current_section = 'requirements'
        elif any(x in line.lower() for x in ['benefit', 'perks', 'offer']):
            current_section = 'benefits'
        
        # Add bullet points to current section
        if line_clean.startswith('•') or line_clean.startswith('-') or line_clean.startswith('*'):
            bullet = line_clean[1:].strip()
            if current_section and bullet:
                job_info[current_section].append(bullet)
    
    # Full description
    job_info["description"] = markdown_content
    
    logger.info(f"Extracted: Title={job_info['title']}, Location={job_info['location']}")
    return job_info


async def main():
    """Main function to demonstrate LinkedIn job scraping."""
    
    # Test URLs
    job_urls = [
        "https://www.linkedin.com/jobs/view/4367883495"
    ]
    
    for job_url in job_urls:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {job_url}")
        logger.info(f"{'='*60}\n")
        
        result = await scrape_linkedin_job(job_url)
        
        if result:
            metadata = result.get("metadata", {})
            extracted = result.get("extracted_data", {})
            
            # Display results
            print("\n📋 JOB INFORMATION:")
            print(f"  Title: {extracted.get('title', 'N/A')}")
            print(f"  Company: {extracted.get('company', 'N/A')}")
            print(f"  Location: {extracted.get('location', 'N/A')}")
            print(f"  Job Type: {extracted.get('job_type', 'N/A')}")
            print(f"\n📊 METADATA:")
            print(f"  Content Length: {metadata.get('content_length', 'N/A')} characters")
            print(f"  Scraped At: {metadata.get('scraped_at', 'N/A')}")
            
            responsibilities = extracted.get('responsibilities', [])
            if responsibilities:
                print(f"\n✅ RESPONSIBILITIES ({len(responsibilities)}):")
                for resp in responsibilities[:5]:  # Show first 5
                    print(f"  • {resp[:80]}...")
            
            requirements = extracted.get('requirements', [])
            if requirements:
                print(f"\n🎯 REQUIREMENTS ({len(requirements)}):")
                for req in requirements[:5]:  # Show first 5
                    print(f"  • {req[:80]}...")
            
            # Save to JSON
            output_file = f"job_data_{int(time.time())}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Data saved to {output_file}")
        else:
            logger.error("Failed to scrape job")
    
if __name__ == "__main__":
    asyncio.run(main())
