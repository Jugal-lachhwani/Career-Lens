"""
Automated tests for /career-chat endpoint.

These tests mock the CareerLens bot and workflow to keep tests deterministic
and avoid live dependencies.
"""

import os
import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

# Provide safe defaults so importing src.api does not fail in test environments.
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "job_ai_agent")

API_IMPORT_ERROR = None
api_module = None
try:
    import src.api as api_module
except ModuleNotFoundError as exc:
    API_IMPORT_ERROR = str(exc)


class _FakeBot:
    def answer(self, **kwargs):
        question = kwargs.get("question", "")
        if "trending" in question.lower():
            answer = "Top trends point to strong demand in AI Engineer and Data Engineer roles."
            analytics_used = True
        else:
            answer = "Focus on Python, SQL, and cloud fundamentals this month."
            analytics_used = False

        return SimpleNamespace(
            answer=answer,
            tools_used=["analytics_snapshot" if analytics_used else "none"],
            analytics_used=analytics_used,
            live_jobs_used=False,
            live_jobs_count=0,
            top_skill_gaps=["docker", "system design"],
        )


@unittest.skipIf(api_module is None, f"Skipping API tests due to missing dependency: {API_IMPORT_ERROR}")
class CareerChatApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_get_workflow = api_module.get_workflow
        cls._original_get_career_bot = api_module.get_career_bot

        api_module.get_workflow = lambda: SimpleNamespace(app=SimpleNamespace(invoke=lambda _: {}))
        api_module.get_career_bot = lambda: _FakeBot()

        def _fake_postgres_session():
            yield object()

        api_module.app.dependency_overrides[api_module.get_postgres_session] = _fake_postgres_session
        cls.client = TestClient(api_module.app)

    @classmethod
    def tearDownClass(cls):
        api_module.get_workflow = cls._original_get_workflow
        api_module.get_career_bot = cls._original_get_career_bot
        api_module.app.dependency_overrides.clear()

    def test_career_chat_success_text_only(self):
        response = self.client.post(
            "/career-chat",
            data={"question": "Which skills should I learn next?"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIn("answer", body)
        self.assertIn("top_skill_gaps", body)

    def test_career_chat_uses_analytics_for_trending_question(self):
        response = self.client.post(
            "/career-chat",
            data={"question": "What are the trending jobs now?"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["analytics_used"])
        self.assertIn("Top trends", body["answer"])

    def test_career_chat_rejects_non_pdf_resume(self):
        response = self.client.post(
            "/career-chat",
            data={"question": "Match my resume with live jobs", "force_live_jobs": "true"},
            files={"resume": ("resume.txt", b"fake content", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("Only PDF", body["detail"])


if __name__ == "__main__":
    unittest.main()
