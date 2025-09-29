"""Reasoner agent that produces explanations and timelines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from api.models.schemas import CaseCategory, CaseReasoningResponse, LawCitation, ReasoningStep
from llm import ChatMessage, LLMClient


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
            " Respond in JSON with keys explanation, steps, deadlines, citations."\
            " #agent:reasoner"
        )
        user_prompt = json.dumps(
            {
                "category": payload.category.value,
                "facts": payload.facts,
                "law": payload.law_summaries,
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
        data = json.loads(raw)
        explanation = data.get("explanation", "")
        steps = data.get("steps", [])
        citation_dicts = data.get("citations", [])
        deadlines_payload = data.get("deadlines", [])
        citations = [
            LawCitation(
                url=item["url"],
                point=item.get("point", ""),
                as_of=date.fromisoformat(item.get("as_of", date.today().isoformat())),
            )
            for item in citation_dicts
        ]
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
            steps=steps,
            law_citations=citations,
            deadlines=deadlines,
            as_of_date=today,
        )
