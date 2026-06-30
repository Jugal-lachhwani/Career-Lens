# Import required libraries
import asyncio
import nest_asyncio
from crawl4ai import AsyncWebCrawler

# Allow nested event loops (important for Jupyter / notebooks)
nest_asyncio.apply()
print("✅ Libraries imported successfully")


async def scrape_linkedin_job():
    """
    Scrape a single LinkedIn job page (no query params).
    """
    job_url = "https://www.linkedin.com/jobs/view/4370001375"
    print(f"🔍 Scraping job page: {job_url}")

    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(
            url=job_url,
            bypass_cache=True,

            # Wait until job details load
            wait_for="css:.top-card-layout__entity-info",

            # Scroll slightly to ensure description loads
            js_code=[
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(r => setTimeout(r, 2000));"
            ],

            # Extract only the job description section
            css_selector=".jobs-description"
        )

        if result.success:
            print("✅ Job page scraped successfully!")
            print(f"📄 Content length: {len(result.markdown)}")
            return result.markdown
        else:
            print("❌ Scraping failed")
            print(result.error_message)
            return None


# Example usage
async def main():
    job_data = await scrape_linkedin_job()
    print("\n===== JOB CONTENT =====\n")
    print(job_data)


if __name__ == "__main__":
    asyncio.run(main())
