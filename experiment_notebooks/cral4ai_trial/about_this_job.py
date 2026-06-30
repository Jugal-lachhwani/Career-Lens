# DOnt use it
# Import required libraries
import asyncio
import nest_asyncio
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup

# Allow nested event loops (important for Jupyter / notebooks)
nest_asyncio.apply()
print("✅ Libraries imported successfully")

async def scrape_linkedin_job_about():
    """
    Extract the About the Job section from LinkedIn.
    Captures headings, bullet points, and normal paragraphs nicely.
    """
    job_url = "https://www.linkedin.com/jobs/view/4357605013"
    print(f"🔍 Scraping About the Job content from: {job_url}")

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=job_url,
            bypass_cache=True,
            wait_for='css:[data-testid="expandable-text-box"]',
            js_code=[
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(r => setTimeout(r, 2000));"
            ],
            css_selector='[data-testid="expandable-text-box"]'
        )

        if not result.success:
            print("❌ Failed to extract About the Job content")
            print(result.error_message)
            return None

        soup = BeautifulSoup(result.html, 'html.parser')

        # Initialize a list to hold formatted text
        formatted_lines = []

        # Loop over all children elements inside the container
        container = soup
        for elem in container.descendants:
            if elem.name in ['h3', 'h4', 'strong']:
                # Headings
                text = elem.get_text(strip=True)
                if text:
                    formatted_lines.append(f"### {text}")
            elif elem.name == 'p':
                # Normal paragraph
                text = elem.get_text(strip=True)
                if text:
                    formatted_lines.append(text)
            elif elem.name == 'li':
                # Bullet points
                text = elem.get_text(strip=True)
                if text:
                    formatted_lines.append(f"- {text}")

        # Join everything as a Markdown-friendly string
        about_job_text = "## About the job\n\n" + "\n\n".join(formatted_lines)

        print("✅ About the job content extracted cleanly")
        return about_job_text

# Example usage
async def main():
    content = await scrape_linkedin_job_about()
    print("\n========== ABOUT THE JOB ==========\n")
    print(content)

if __name__ == "__main__":
    asyncio.run(main())
