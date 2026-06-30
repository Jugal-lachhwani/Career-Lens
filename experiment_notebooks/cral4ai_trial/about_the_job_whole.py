# Import required libraries
import asyncio
import nest_asyncio
import re
from crawl4ai import AsyncWebCrawler

# Allow nested event loops (important for Jupyter / notebooks)
nest_asyncio.apply()
print("✅ Libraries imported successfully")


async def scrape_linkedin_job_about():
    """
    Scrape the complete 'About the job' section from a LinkedIn job page
    using stable DOM attributes (NO API KEY REQUIRED).
    """

    job_url = "https://www.linkedin.com/jobs/view/4369367348"
    print(f"🔍 Scraping About the Job from: {job_url}")

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=job_url,
            bypass_cache=True,

            # Wait until the About The Job component is loaded
            wait_for='css:[componentkey^="JobDetails_AboutTheJob"]',

            # Small scroll to trigger lazy content
            js_code=[
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(r => setTimeout(r, 2000));"
            ],

            # Extract the ENTIRE About the Job block (heading + content)
            css_selector='[componentkey^="JobDetails_AboutTheJob"]'
        )

        if result.success:
            print("✅ Successfully scraped About the job section")
            print(f"📄 Extracted content length: {len(result.markdown)}")
            
            # Get the raw job description
            text = result.markdown

            # Step 1: Truncate at "Show more  Show less"
            pattern_truncate = r'^(.*?Show more  Show less).*$'
            text = re.sub(pattern_truncate, r'\1', text, flags=re.DOTALL)

            # Step 2: Remove markdown links
            pattern_links = r'\[([^\]]+)\]\([^)]*\)'
            text = re.sub(pattern_links, r'\1', text)

            # Step 3: Remove image references
            pattern_images = r'!\[([^\]]*)\]\([^)]*\)'
            text = re.sub(pattern_images, '', text)

            print("\n✅ Cleaned job description")
            return text
        else:
            print("❌ Scraping failed")
            print(result.error_message)
            return None


# Example usage
async def main():
    about_job_content = await scrape_linkedin_job_about()

    print("\n========== ABOUT THE JOB ==========\n")
    print(about_job_content)


if __name__ == "__main__":
    asyncio.run(main())
