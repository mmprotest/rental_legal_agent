"""Intake agent that classifies renter issues and flags risks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

from api.models.schemas import CaseCategory, IntakeRequest
from llm import ChatMessage, LLMClient


@dataclass
class IntakeResult:
    category: CaseCategory
    subcategory: Optional[str]
    risk_flags: List[str]
    next_questions: List[str]


class IntakeAgent:
    """Use an LLM to interpret renter intake responses."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def run(self, request: IntakeRequest) -> IntakeResult:
        system_prompt = (
            "You are the intake classifier for a Victorian renter legal assistant. "
            "Classify the renter issue using the allowed categories and flag urgent repairs."
            " Respond ONLY with JSON. #agent:intake"
        )
        user_prompt = json.dumps(
            {
                "issue": request.issue,
                "free_text": request.free_text,
                "answers": request.answers,
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
        category = CaseCategory(data.get("category", "repairs_nonurgent"))
        return IntakeResult(
            category=category,
            subcategory=data.get("subcategory"),
            risk_flags=data.get("risk_flags", []),
            next_questions=data.get("next_questions", []),
        )
