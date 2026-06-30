# Import required libraries
import asyncio
import nest_asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.chunking_strategy import RegexChunking
import json

# Allow nested event loops (important for Jupyter)
nest_asyncio.apply()
print("✅ Libraries imported successfully")


async def scrape_linkedin_search(search_query, location="India"):
    """
    Scrape LinkedIn job search results.
    
    Args:
        search_query: Job title or keywords (e.g., "Software Engineer")
        location: Job location (e.g., "India", "Bangalore")
    """
    # Construct LinkedIn search URL
    base_url = "https://www.linkedin.com/jobs/search/"
    params = f"?keywords={search_query.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
    search_url = base_url + params
    
    print(f"🔍 Searching: {search_url}")
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=search_url,
            bypass_cache=True,
            # Wait for job cards to load
            wait_for="css:.jobs-search__results-list",
            js_code=[
                # Scroll to load more jobs
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(r => setTimeout(r, 3000));",
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(r => setTimeout(r, 2000));"
            ],
            css_selector=".jobs-search__results-list"
        )
        
        if result.success:
            print("✅ Successfully scraped search results!")
            print(f"Content length: {len(result.markdown)}")
            return result.markdown
        else:
            print(f"❌ Failed: {result.error_message}")
            return None

# Example usage
async def main():
    results = await scrape_linkedin_search("Python Developer", "Bangalore")
    print(results)
    
if __name__ == "__main__":
    asyncio.run(main())