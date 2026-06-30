"""
Google Sheets Writer Module for Job Search Agent.

Handles authentication and writing of Job objects to a configured Google Sheet.
"""

import os
import logging
from typing import List

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from dotenv import load_dotenv

from src.state import Job

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Path to store the OAuth token so login is only required once
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "credentials", "token.pickle")


def _get_credentials() -> Credentials:
    """
    Load stored OAuth credentials or run the browser-based login flow.
    On first run, a browser window will open asking you to authorise access.
    The token is saved to credentials/token.pickle for reuse.
    """
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token_file:
            creds = pickle.load(token_file)

    # Refresh expired token automatically
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "wb") as token_file:
            pickle.dump(creds, token_file)
        return creds

    # No valid token — run the consent screen in the browser
    if not creds or not creds.valid:
        client_secret_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
        if not client_secret_path or not os.path.exists(client_secret_path):
            raise FileNotFoundError(
                f"OAuth client secret file not found at: {client_secret_path}. "
                "Set GOOGLE_SHEETS_CREDENTIALS_PATH in your .env file."
            )
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as token_file:
            pickle.dump(creds, token_file)

    return creds


def _get_worksheet():
    """Authorize and return the configured worksheet object."""
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    worksheet_name = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Jobs")

    if not spreadsheet_id:
        logger.warning("GOOGLE_SHEETS_SPREADSHEET_ID not set. Skipping Google Sheets write.")
        return None

    try:
        creds = _get_credentials()
        client = gspread.authorize(creds)
        sheet = client.open_by_key(spreadsheet_id)

        try:
            ws = sheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            logger.info("Worksheet '%s' not found. Creating it.", worksheet_name)
            ws = sheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)

        return ws

    except Exception as e:
        logger.error("Failed to connect to Google Sheets: %s", e, exc_info=True)
        return None


def write_jobs_to_sheet(jobs: List[Job]) -> bool:
    """
    Appends a list of Job objects as new rows in the configured Google Sheet.

    Returns True on success, False on failure.
    """
    if not jobs:
        logger.info("No jobs to write to Google Sheets.")
        return False

    ws = _get_worksheet()
    if not ws:
        return False

    logger.info("Writing %d jobs to Google Sheet.", len(jobs))

    try:
        header = list(Job.model_fields.keys())

        # Add header row only if the sheet is empty
        if not ws.get_all_values():
            ws.append_row(header, value_input_option="RAW")

        rows_to_append = [
            [str(getattr(job, field, "")) for field in header]
            for job in jobs
        ]

        ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")
        logger.info("Successfully wrote %d jobs to Google Sheet.", len(jobs))
        return True

    except Exception as e:
        logger.error("Failed to write jobs to Google Sheet: %s", e, exc_info=True)
        return False
