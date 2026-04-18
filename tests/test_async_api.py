"""
Async-aware test client for CareerLens API (Phase 3 — Celery architecture).

Flow:
  1. POST /process-job-search  →  202 Accepted  { task_id, poll_url }
  2. GET  /tasks/{task_id}     →  poll until status == "complete" | "failed"
  3. Print full result.

Usage:
  python tests/test_async_api.py
  python tests/test_async_api.py --resume path/to/resume.pdf
  python tests/test_async_api.py --resume path/to/resume.pdf --query "ML Engineer jobs in Bangalore"
"""

import argparse
import json
import os
import time
import sys
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_URL      = "http://localhost:8000"
RESUME_PATH  = Path(r"E:\Genai_Projects\Job_search_Agent - Copy\Resume.pdf")
POLL_INTERVAL = 5      # seconds between status polls
POLL_TIMEOUT  = 600    # seconds before giving up

# API key — reads from env, falls back to the dev key in .env
API_KEY: str = os.getenv("API_KEYS", "clens-dev-local-key").split(",")[0].strip()
AUTH_HEADERS: dict = {"X-API-Key": API_KEY} if API_KEY else {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _separator(title: str = "", width: int = 80) -> None:
    if title:
        pad = (width - len(title) - 2) // 2
        print("=" * pad + f" {title} " + "=" * pad)
    else:
        print("=" * width)


def _ok(msg: str)   -> None: print(f"  [OK]   {msg}")
def _err(msg: str)  -> None: print(f"  [ERR]  {msg}")
def _info(msg: str) -> None: print(f"  [INFO] {msg}")


# ---------------------------------------------------------------------------
# Individual test functions
# ---------------------------------------------------------------------------

def test_root() -> bool:
    """GET / — API info."""
    _separator("GET /")
    try:
        r = requests.get(f"{API_URL}/", timeout=10)
        print(json.dumps(r.json(), indent=2))
        _ok(f"Status {r.status_code}")
        return r.status_code == 200
    except Exception as exc:
        _err(str(exc))
        return False


def test_health() -> bool:
    """GET /health — liveness probe."""
    _separator("GET /health")
    try:
        r = requests.get(f"{API_URL}/health", timeout=10)
        print(json.dumps(r.json(), indent=2))
        _ok(f"Status {r.status_code}")
        return r.status_code == 200
    except Exception as exc:
        _err(str(exc))
        return False


def test_get_jobs(limit: int = 5) -> bool:
    """GET /jobs — check DB-backed job listing."""
    _separator(f"GET /jobs?limit={limit}")
    try:
        r = requests.get(f"{API_URL}/jobs", params={"limit": limit}, timeout=10)
        body = r.json()
        _ok(f"Status {r.status_code} — {body.get('count', 0)} job(s) returned")
        if body.get("jobs"):
            print(json.dumps(body["jobs"][0], indent=2, default=str))
        return r.status_code == 200
    except Exception as exc:
        _err(str(exc))
        return False


def test_search_history(limit: int = 3) -> bool:
    """GET /search-history."""
    _separator(f"GET /search-history?limit={limit}")
    try:
        r = requests.get(f"{API_URL}/search-history", params={"limit": limit}, timeout=10)
        body = r.json()
        _ok(f"Status {r.status_code} — {body.get('count', 0)} record(s)")
        if body.get("history"):
            print(json.dumps(body["history"][0], indent=2, default=str))
        return r.status_code == 200
    except Exception as exc:
        _err(str(exc))
        return False


def test_analytics_dashboard() -> bool:
    """GET /analytics/dashboard — PostgreSQL aggregation."""
    _separator("GET /analytics/dashboard")
    try:
        r = requests.get(f"{API_URL}/analytics/dashboard", timeout=15)
        body = r.json()
        summary = body.get("summary", {})
        _ok(
            f"Status {r.status_code} — "
            f"total_jobs={summary.get('total_jobs')} | "
            f"unique_skills={summary.get('unique_skills')}"
        )
        print(f"  Top skills (first 5): {body.get('top_skills', [])[:5]}")
        return r.status_code == 200
    except Exception as exc:
        _err(str(exc))
        return False


def test_chat_sessions() -> bool:
    """GET /career-chat/sessions."""
    _separator("GET /career-chat/sessions")
    try:
        r = requests.get(f"{API_URL}/career-chat/sessions", timeout=10)
        sessions = r.json()
        _ok(f"Status {r.status_code} — {len(sessions)} session(s)")
        if sessions:
            print(json.dumps(sessions[0], indent=2, default=str))
        return r.status_code == 200
    except Exception as exc:
        _err(str(exc))
        return False


def test_job_search_async(user_input: str, resume_path: Path) -> bool:
    """
    Full async job-search flow:
      POST /process-job-search  →  202  { task_id }
      GET  /tasks/{task_id}     →  poll until complete / failed
    """
    _separator("POST /process-job-search  (async)")

    # --- 1. Validate resume -----------------------------------------------
    if not resume_path.exists():
        _err(f"Resume not found: {resume_path}")
        _info("Update RESUME_PATH at the top of this file, or pass --resume <path>")
        return False

    _info(f"Query : {user_input}")
    _info(f"Resume : {resume_path}")

    # --- 2. Submit job -------------------------------------------------------
    try:
        with open(resume_path, "rb") as f:
            response = requests.post(
                f"{API_URL}/process-job-search",
                files={"resume": ("resume.pdf", f, "application/pdf")},
                data={"user_input": user_input},
                headers=AUTH_HEADERS,     # Phase 4 — send API key
                timeout=30,
            )
    except Exception as exc:
        _err(f"POST failed: {exc}")
        return False

    if response.status_code != 202:
        _err(f"Expected 202 Accepted, got {response.status_code}")
        _err(response.text)
        return False

    body     = response.json()
    task_id  = body["task_id"]
    poll_url = body["poll_url"]
    _ok(f"Task accepted — task_id: {task_id}")
    _info(f"Poll URL: {poll_url}")

    # --- 3. Poll for result --------------------------------------------------
    _separator("Polling GET /tasks/{task_id}")
    start    = time.time()
    attempt  = 0

    while True:
        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT:
            _err(f"Timed out after {int(elapsed)}s waiting for task to complete")
            return False

        attempt += 1
        try:
            poll_response = requests.get(
                f"{API_URL}/tasks/{task_id}", timeout=10
            )
            poll_body = poll_response.json()
        except Exception as exc:
            _err(f"Poll attempt {attempt} failed: {exc}")
            time.sleep(POLL_INTERVAL)
            continue

        status = poll_body.get("status", "unknown")
        print(
            f"  [{int(elapsed):>4}s]  attempt {attempt:>3}  ->  status: {status}",
            flush=True,
        )

        if status == "complete":
            _ok(f"Task completed in {int(elapsed)}s!")
            result = poll_body.get("result", {})
            _print_job_result(result)
            return True

        elif status == "failed":
            _err(f"Task failed: {poll_body.get('error')}")
            return False

        # still pending / running — wait and retry
        time.sleep(POLL_INTERVAL)


def _print_job_result(result: dict) -> None:
    """Pretty-print the deserialized workflow result."""
    if not result:
        _info("Result payload is empty.")
        return

    _separator("Result Summary")

    # Job summaries
    summaries = result.get("job_summaries", [])
    print(f"\n  --- Job Summaries ({len(summaries)} found) ---")
    for i, job in enumerate(summaries[:5], 1):
        print(f"\n    [{i}] {job.get('job_info', '')[:120]}")
        skills = job.get("job_skills", [])
        print(f"        Skills: {', '.join(skills[:6])}")

    # Feedback
    feedbacks = result.get("job_feedbacks", [])
    print(f"\n  --- Similarity Scores ({len(feedbacks)} jobs) ---")
    for fb in feedbacks[:5]:
        print(
            f"    Job {fb.get('id', '?')}  ->  "
            f"Score: {fb.get('similarity', '?')}/100  |  "
            f"{str(fb.get('feedback', ''))[:100]}"
        )

    # Resume
    rf = result.get("resume_fields", {})
    if rf:
        print(f"\n  --- Resume Skills (top 8) ---")
        print(f"    {', '.join((rf.get('skills') or [])[:8])}")

    print()


def test_career_chat(question: str = "What Python skills are most in demand right now?") -> bool:
    """POST /career-chat — quick chat (no resume)."""
    _separator("POST /career-chat")
    _info(f"Question: {question}")
    try:
        r = requests.post(
            f"{API_URL}/career-chat",
            data={"question": question},
            headers=AUTH_HEADERS,     # Phase 4 — send API key
            timeout=60,
        )
        if r.status_code == 200:
            body = r.json()
            _ok(f"Status {r.status_code} — session_id={body.get('session_id')}")
            print(f"\n  Answer (first 400 chars):\n  {body.get('answer', '')[:400]}")
            print(f"\n  Tools used : {body.get('tools_used')}")
            print(f"  Analytics  : {body.get('analytics_used')}")
        else:
            _err(f"Status {r.status_code}: {r.text[:300]}")
        return r.status_code == 200
    except Exception as exc:
        _err(str(exc))
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="CareerLens API test client")
    parser.add_argument("--resume", default=str(RESUME_PATH),
                        help="Path to a PDF resume (for job-search test)")
    parser.add_argument("--query",  default="Find 2 ML Engineer jobs in Bangalore with 2 years experience",
                        help="Job search query string")
    parser.add_argument("--skip-search", action="store_true",
                        help="Skip the long-running async job-search test")
    parser.add_argument("--skip-chat",   action="store_true",
                        help="Skip the career-chat test (needs LLM)")
    args = parser.parse_args()

    resume = Path(args.resume)

    _separator("CareerLens API Test Suite", width=80)
    print(f"  Target  : {API_URL}")
    print(f"  Resume  : {resume}")
    print(f"  API Key : {API_KEY[:12]}... (from API_KEYS env / default)")
    print()

    results: dict[str, bool] = {}

    # --- Fast / read-only endpoints -----------------------------------------
    results["GET /"]                    = test_root()
    results["GET /health"]              = test_health()
    results["GET /jobs"]                = test_get_jobs()
    results["GET /search-history"]      = test_search_history()
    results["GET /analytics/dashboard"] = test_analytics_dashboard()
    results["GET /career-chat/sessions"]= test_chat_sessions()

    # --- Career chat (LLM call, ~5-15s) ------------------------------------
    if not args.skip_chat:
        results["POST /career-chat"] = test_career_chat()
    else:
        _info("Skipping career-chat test (--skip-chat)")

    # --- Async job search (60-120s) -----------------------------------------
    if not args.skip_search:
        results["POST /process-job-search (async)"] = test_job_search_async(
            user_input=args.query,
            resume_path=resume,
        )
    else:
        _info("Skipping async job-search test (--skip-search)")

    # --- Final report -------------------------------------------------------
    _separator("Test Report", width=80)
    passed = sum(v for v in results.values())
    total  = len(results)

    for name, ok in results.items():
        icon = "[PASS]" if ok else "[FAIL]"
        print(f"  {icon}  {name}")

    print()
    print(f"  {'All passed!' if passed == total else f'{total - passed} test(s) FAILED'}"
          f"  ({passed}/{total})")
    _separator(width=80)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(130)
    except requests.exceptions.ConnectionError:
        _err("Cannot connect to API! Is `python run_api.py` running?")
        sys.exit(1)
