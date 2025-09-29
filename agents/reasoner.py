"""Reasoner agent that produces explanations and timelines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from api.models.schemas import CaseCategory, CaseReasoningResponse, LawCitation, ReasoningStep
from llm import ChatMessage, LLMClient, safe_json_loads


@dataclass
class ReasonerInput:
    category: CaseCategory
    facts: dict[str, str]
    law_summaries: List[dict[str, str]]


class ReasonerAgent:
    """Use the LLM to compose a plain-English explanation and plan."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def run(self, payload: ReasonerInput) -> CaseReasoningResponse:
        system_prompt = (
            "You are a compliance-locked legal explainer for Victorian renters."
            " Only use the supplied law snippets."
            " Respond ONLY with a compact JSON object with keys: explanation, steps, deadlines, citations."
            " Do not include any prose before or after the JSON. #agent:reasoner"
        )
        # Provide a compact schema and explicit tasking for higher answer quality
        user_prompt = json.dumps(
            {
                "task": "answer",
                "question": payload.facts.get("question") or payload.facts.get("issue") or "",
                "context": {
                    "category": payload.category.value,
                    "facts": payload.facts,
                    "law": payload.law_summaries,
                },
                "constraints": {
                    "jurisdiction": "Victoria, Australia",
                    "citations_required": True,
                },
                "output_schema": {
                    "explanation": "string",
                    "steps": ["string"],
                    "deadlines": [{"title": "string", "description": "string", "due_in_days": "number"}],
                    "citations": [{"url": "string", "point": "string", "as_of": "YYYY-MM-DD"}],
                },
            }
        )
        raw = self.llm.chat(
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ],
            temperature=0.2,
            response_format="json_object",
        )
        data = safe_json_loads(raw)
        if not data:
            # Minimal deterministic fallback based on provided law
            law_points = [item.get("summary", "") for item in payload.law_summaries]
            explanation = " ".join(law_points)[:600]
            return CaseReasoningResponse(
                explanation_plain=explanation,
                steps=[],
                law_citations=[],
                deadlines=[],
                as_of_date=date.today(),
            )
        explanation = data.get("explanation", "")
        steps = data.get("steps", [])
        # Normalize steps: accept list of strings or list of dicts with title/description
        norm_steps: List[str] = []
        for item in steps:
            if isinstance(item, str):
                norm_steps.append(item)
            elif isinstance(item, dict):
                title = item.get("title") or item.get("step") or "Step"
                desc = item.get("description") or ""
                norm_steps.append(f"{title}: {desc}".strip())
        citation_dicts = data.get("citations", [])
        deadlines_payload = data.get("deadlines", [])
        citations: List[LawCitation] = []
        for item in citation_dicts:
            try:
                citations.append(
                    LawCitation(
                        url=item.get("url", ""),
                        point=item.get("point", ""),
                        as_of=date.fromisoformat(item.get("as_of", date.today().isoformat())),
                    )
                )
            except Exception:
                # Skip malformed citation entries
                continue
        deadlines: List[ReasoningStep] = []
        today = date.today()
        for deadline in deadlines_payload:
            due_in_days = deadline.get("due_in_days")
            due_date = today + timedelta(days=int(due_in_days)) if due_in_days is not None else None
            deadlines.append(
                ReasoningStep(
                    title=deadline.get("title", "Next step"),
                    description=deadline.get("description", ""),
                    due_date=due_date,
                )
            )
        return CaseReasoningResponse(
            explanation_plain=explanation,
            steps=norm_steps,
            law_citations=citations,
            deadlines=deadlines,
            as_of_date=today,
        )
