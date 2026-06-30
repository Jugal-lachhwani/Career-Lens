"""
CareerLens chatbot module.

This service routes user questions to internal tools:
- analytics snapshot from PostgreSQL job features
- live job search + resume matching workflow
and returns a coach-style response.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from collections import Counter
import re
import logging

from langchain_core.prompts import PromptTemplate
from src.llm_factory import get_text_llm

logger = logging.getLogger(__name__)


@dataclass
class CareerChatResult:
    answer: str
    tools_used: list[str]
    analytics_used: bool
    live_jobs_used: bool
    live_jobs_count: int
    top_skill_gaps: list[str]


class CareerLensBot:
    def __init__(self):
        self.llm = get_text_llm(temperature=0.3)

    @staticmethod
    def _canonical_role_from_title(title: str) -> str:
        t = (title or "").lower()
        if any(k in t for k in ["ai engineer", "genai", "llm", "prompt engineer"]):
            return "AI Engineer"
        if any(k in t for k in ["machine learning engineer", "ml engineer", "applied scientist"]):
            return "ML Engineer"
        if any(k in t for k in ["data scientist"]):
            return "Data Scientist"
        if any(k in t for k in ["data engineer", "analytics engineer"]):
            return "Data Engineer"
        if any(k in t for k in ["data analyst", "business analyst", "bi analyst"]):
            return "Data Analyst"
        if any(k in t for k in ["backend", "back-end", "server-side"]):
            return "Backend Engineer"
        if any(k in t for k in ["frontend", "front-end", "ui engineer", "react developer"]):
            return "Frontend Engineer"
        if any(k in t for k in ["full stack", "full-stack", "fullstack"]):
            return "Full Stack Engineer"
        if any(k in t for k in ["software engineer", "software developer", "application engineer"]):
            return "Software Engineer"
        if any(k in t for k in ["devops", "site reliability", "sre", "platform engineer"]):
            return "DevOps Engineer"
        return "Other"

    @staticmethod
    def _extract_transition_roles(question: str) -> tuple[Optional[str], Optional[str]]:
        q = question.lower()

        # Pattern: migrate/switch/transition from X to Y
        match = re.search(
            r"(?:migrate|switch|transition|move)\s*(?:from)?\s*([a-z\s\-]+?)\s*to\s*([a-z\s\-]+)",
            q,
        )
        if not match:
            return None, None

        source_raw = match.group(1).strip()
        target_raw = match.group(2).strip()

        source_role = CareerLensBot._canonical_role_from_title(source_raw)
        target_role = CareerLensBot._canonical_role_from_title(target_raw)

        source_role = source_role if source_role != "Other" else source_raw.title()
        target_role = target_role if target_role != "Other" else target_raw.title()
        return source_role, target_role

    @staticmethod
    def _needs_analytics(question: str) -> bool:
        q = question.lower()
        analytics_keywords = [
            "trend",
            "trending",
            "market",
            "analytics",
            "dashboard",
            "plot",
            "chart",
            "skill",
            "demand",
            "role",
        ]
        return any(k in q for k in analytics_keywords)

    @staticmethod
    def _needs_live_jobs(question: str, force_live: bool) -> bool:
        if force_live:
            return True
        q = question.lower()
        live_keywords = [
            "live jobs",
            "latest jobs",
            "find jobs",
            "match my resume",
            "resume match",
            "search jobs",
            "current openings",
        ]
        return any(k in q for k in live_keywords)

    @staticmethod
    def _analytics_snapshot(postgres_session, job_features_model) -> dict[str, Any]:
        rows = postgres_session.query(job_features_model).all()
        if not rows:
            return {
                "total_jobs": 0,
                "top_roles": [],
                "top_skills": [],
                "top_locations": [],
                "role_skill_map": {},
            }

        role_counter = Counter()
        skill_counter = Counter()
        location_counter = Counter()
        role_skill_counter: dict[str, Counter] = {}

        for row in rows:
            raw_title = (row.title or "Unknown").strip() or "Unknown"
            canonical_role = CareerLensBot._canonical_role_from_title(raw_title)
            role_counter[canonical_role] += 1

            location = (row.location or "Unknown").strip() or "Unknown"
            location_counter[location] += 1

            if canonical_role not in role_skill_counter:
                role_skill_counter[canonical_role] = Counter()

            for skill in (row.skills or []):
                cleaned = str(skill).strip()
                if cleaned:
                    skill_counter[cleaned] += 1
                    role_skill_counter[canonical_role][cleaned] += 1

        role_skill_map = {
            role: [skill for skill, _ in counter.most_common(12)]
            for role, counter in role_skill_counter.items()
        }

        return {
            "total_jobs": len(rows),
            "top_roles": [{"role": k, "count": v} for k, v in role_counter.most_common(8)],
            "top_skills": [{"skill": k, "count": v} for k, v in skill_counter.most_common(12)],
            "top_locations": [
                {"location": k, "count": v} for k, v in location_counter.most_common(8)
            ],
            "role_skill_map": role_skill_map,
        }

    @staticmethod
    def _run_live_workflow(workflow, user_query: str, resume_path: str) -> dict[str, Any]:
        initial_state = {
            "user_input": user_query,
            "resume_path": resume_path,
            "visited_ids": set(),
            "visited_ids_feedback": set(),
        }
        final_state = workflow.app.invoke(initial_state)
        jobs = final_state.get("jobs", [])
        summaries = final_state.get("job_summaries", [])
        feedbacks = final_state.get("job_feedbacks", [])
        resume_fields = final_state.get("resume_fields")

        return {
            "jobs": jobs,
            "summaries": summaries,
            "feedbacks": feedbacks,
            "resume_fields": resume_fields,
        }

    @staticmethod
    def _compute_skill_gaps(live_data: dict[str, Any]) -> list[str]:
        resume_fields = live_data.get("resume_fields")
        summaries = live_data.get("summaries", [])
        if not resume_fields or not summaries:
            return []

        resume_skills = {s.lower().strip() for s in (resume_fields.skills or []) if s}
        required = Counter()
        for summary in summaries:
            for s in (summary.job_skills or []):
                normalized = str(s).lower().strip()
                if normalized:
                    required[normalized] += 1

        gaps = [skill for skill, _ in required.most_common() if skill not in resume_skills]
        return gaps[:8]

    @staticmethod
    def _compose_tool_grounded_answer(
        question: str,
        analytics: Optional[dict[str, Any]],
        live_data: Optional[dict[str, Any]],
        top_skill_gaps: list[str],
        requested_live_jobs: bool,
        resume_provided: bool,
    ) -> str:
        lines: list[str] = []
        lines.append("CareerLens Guidance")

        source_role, target_role = CareerLensBot._extract_transition_roles(question)

        if analytics and analytics.get("total_jobs", 0) > 0:
            lines.append("")
            lines.append("Market signal from current jobs data:")
            top_roles = analytics.get("top_roles", [])[:4]
            top_skills = analytics.get("top_skills", [])[:8]

            if top_roles:
                role_text = ", ".join([f"{r['role']} ({r['count']})" for r in top_roles])
                lines.append(f"- Most active roles: {role_text}")

            if top_skills:
                skill_text = ", ".join([s["skill"] for s in top_skills])
                lines.append(f"- Most demanded skills: {skill_text}")

        role_skill_map = (analytics or {}).get("role_skill_map", {})
        if target_role and role_skill_map.get(target_role):
            role_top = role_skill_map.get(target_role, [])
            lines.append("")
            lines.append(f"Skills to prioritize for {target_role}:")
            for skill in role_top[:8]:
                lines.append(f"- {skill}")

            if source_role:
                source_top = set(role_skill_map.get(source_role, [])[:12])
                target_top = role_top[:12]
                transition_gaps = [s for s in target_top if s not in source_top]
                if transition_gaps:
                    lines.append("")
                    lines.append(f"Likely transition gaps from {source_role} to {target_role}:")
                    for skill in transition_gaps[:6]:
                        lines.append(f"- {skill}")

        if live_data:
            jobs = live_data.get("jobs", [])
            lines.append("")
            lines.append(f"Live matching result: {len(jobs)} jobs analyzed against your resume.")

            if top_skill_gaps:
                lines.append("Top missing skills from live job requirements:")
                for skill in top_skill_gaps[:6]:
                    lines.append(f"- {skill}")

        if requested_live_jobs and not resume_provided:
            lines.append("")
            lines.append("To run live resume-job matching, upload your resume PDF and re-run with force-live enabled.")

        return "\n".join(lines)

    def answer(
        self,
        *,
        question: str,
        postgres_session,
        job_features_model,
        workflow,
        chat_history: Optional[list[dict[str, str]]] = None,
        resume_path: Optional[str] = None,
        live_job_query: Optional[str] = None,
        force_live_jobs: bool = False,
    ) -> CareerChatResult:
        tools_used: list[str] = []
        analytics_used = self._needs_analytics(question)
        live_jobs_used = self._needs_live_jobs(question, force_live_jobs)

        analytics = None
        if analytics_used:
            tools_used.append("analytics_snapshot")
            analytics = self._analytics_snapshot(postgres_session, job_features_model)

        live_data = None
        if live_jobs_used and resume_path:
            tools_used.append("live_job_resume_match")
            query = live_job_query or question
            live_data = self._run_live_workflow(workflow, query, resume_path)
        elif live_jobs_used and not resume_path:
            tools_used.append("live_job_resume_match_skipped_no_resume")

        live_jobs_count = len((live_data or {}).get("jobs", []))
        top_skill_gaps = self._compute_skill_gaps(live_data or {})

        tool_grounded_answer = self._compose_tool_grounded_answer(
            question=question,
            analytics=analytics,
            live_data=live_data,
            top_skill_gaps=top_skill_gaps,
            requested_live_jobs=live_jobs_used,
            resume_provided=bool(resume_path),
        )

        coach_prompt = PromptTemplate(
            template=(
                "You are CareerLens, a practical and motivating career mentor.\n"
                "Answer the user question using available tool context.\n"
                "Rules:\n"
                "1) Be specific and actionable.\n"
                "2) If analytics are present, explain trends from them.\n"
                "3) If live match context is present, suggest next skill upgrades based on gaps.\n"
                "4) If live jobs were requested but resume is missing, clearly ask user to upload resume.\n"
                "5) Keep answer concise and structured in short sections.\n\n"
                "Conversation history (recent):\n{conversation_history}\n\n"
                "User question:\n{question}\n\n"
                "Analytics context:\n{analytics_context}\n\n"
                "Live jobs context:\n{live_context}\n\n"
                "Top skill gaps:\n{skill_gaps}\n"
            ),
            input_variables=[
                "conversation_history",
                "question",
                "analytics_context",
                "live_context",
                "skill_gaps",
            ],
        )

        analytics_context = analytics if analytics is not None else "No analytics context used"
        live_context = {
            "live_jobs_count": live_jobs_count,
            "top_jobs": [
                {
                    "id": getattr(j, "id", ""),
                    "title": getattr(j, "title", ""),
                    "company": getattr(j, "companyName", ""),
                    "location": getattr(j, "location", ""),
                }
                for j in (live_data or {}).get("jobs", [])[:3]
            ],
        } if live_data else "No live job context used"

        try:
            answer = (coach_prompt | self.llm).invoke(
                {
                    "conversation_history": str(chat_history or []),
                    "question": question,
                    "analytics_context": str(analytics_context),
                    "live_context": str(live_context),
                    "skill_gaps": ", ".join(top_skill_gaps) if top_skill_gaps else "None",
                }
            )

            # Chat models may return message-like objects
            if hasattr(answer, "content"):
                llm_answer = answer.content
            else:
                llm_answer = str(answer)

            # Always include a grounded section from real tools to avoid vague output.
            answer_text = f"{tool_grounded_answer}\n\nCoach note:\n{llm_answer}"

        except Exception as exc:
            logger.warning("CareerLens LLM generation failed; using tool-grounded fallback: %s", exc)
            answer_text = tool_grounded_answer

        return CareerChatResult(
            answer=answer_text,
            tools_used=tools_used,
            analytics_used=analytics_used,
            live_jobs_used=bool(live_data) if live_jobs_used else False,
            live_jobs_count=live_jobs_count,
            top_skill_gaps=top_skill_gaps,
        )
