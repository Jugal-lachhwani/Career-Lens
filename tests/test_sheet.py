"""
test_sheet.py

Verifies the end-to-end Google Sheets integration:
  1. Writes two sample Job rows to the configured sheet.
  2. Reads the sheet back and confirms the rows are present.

Run from the project root:
    python -m tests.test_sheet
"""

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Ensure project root is on the path so 'src' package resolves
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.state import Job
from src.tools.google_sheets_writer import _get_worksheet, write_jobs_to_sheet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Unique marker so we can locate our test rows among any existing data
TEST_MARKER = f"[TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}]"


def build_test_jobs() -> list[Job]:
    return [
        Job(
            id="test-001",
            url="https://example.com/test-job-1",
            title=f"Software Engineer {TEST_MARKER}",
            location="Testville, TS",
            companyName="TestCorp",
            companyUrl="https://linkedin.com/company/testcorp",
            recruiterName="John Doe",
            recruiterUrl="https://linkedin.com/in/johndoe",
            experienceLevel="Mid-Senior level",
            contractType="Full-time",
            workType="Engineering",
            sector="Technology",
            salary="$120,000/yr",
            applyType="EASY_APPLY",
            applyUrl="https://example.com/apply/test-job-1",
            postedTimeAgo="1 day ago",
            postedDate=datetime.now().strftime("%Y-%m-%d"),
            applicationsCount="42",
            description="A test job entry created by the test suite.",
        ),
        Job(
            id="test-002",
            url="https://example.com/test-job-2",
            title=f"Data Analyst {TEST_MARKER}",
            location="Datapolis, DP",
            companyName="Analytics Test Inc.",
            companyUrl="https://linkedin.com/company/analytics-test",
            recruiterName="Jane Smith",
            recruiterUrl="https://linkedin.com/in/janesmith",
            experienceLevel="Entry level",
            contractType="Contract",
            workType="Data & Analytics",
            sector="Finance",
            salary="$85,000/yr",
            applyType="EXTERNAL",
            applyUrl="https://example.com/apply/test-job-2",
            postedTimeAgo="3 hours ago",
            postedDate=datetime.now().strftime("%Y-%m-%d"),
            applicationsCount="10",
            description="Another test job entry for data analysis roles.",
        ),
    ]


def verify_rows_in_sheet(expected_titles: list[str]) -> bool:
    """
    Reads all values from the sheet and checks that every expected title
    (which contains the unique TEST_MARKER) is present.
    """
    ws = _get_worksheet()
    if not ws:
        logger.error("Could not connect to sheet for verification.")
        return False

    all_values = ws.get_all_values()
    flat_text = " | ".join(" ".join(row) for row in all_values)

    missing = [t for t in expected_titles if t not in flat_text]
    if missing:
        logger.error("The following rows were NOT found in the sheet: %s", missing)
        return False

    logger.info("All test rows confirmed present in the sheet.")
    return True


def run_test():
    print("=" * 55)
    print("   Google Sheets Integration Test")
    print("=" * 55)

    # 1. Load environment variables
    load_dotenv()

    # 2. Build test data
    print("\n[1/3] Building sample job data...")
    test_jobs = build_test_jobs()
    print(f"      Created {len(test_jobs)} sample jobs with marker: {TEST_MARKER}")

    # 3. Write to sheet
    print("\n[2/3] Writing jobs to Google Sheet...")
    success = write_jobs_to_sheet(test_jobs)
    if not success:
        print("\n[FAILED] Could not write to sheet. Check logs and .env settings.")
        sys.exit(1)
    print("      Write call completed successfully.")

    # 4. Verify rows were actually added
    print("\n[3/3] Verifying rows are present in the sheet...")
    expected_titles = [job.title for job in test_jobs]
    verified = verify_rows_in_sheet(expected_titles)

    print("\n" + "=" * 55)
    if verified:
        print("  RESULT: PASS - All test rows found in the sheet.")
    else:
        print("  RESULT: FAIL - Some rows were not found. Check logs above.")
    print("=" * 55)

    sys.exit(0 if verified else 1)


if __name__ == "__main__":
    run_test()