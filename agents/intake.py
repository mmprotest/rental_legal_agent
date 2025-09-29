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
        # Be tolerant of arbitrary category strings from the LLM
        raw_category = data.get("category", "repairs_nonurgent")
        try:
            category = CaseCategory(raw_category)
        except Exception:
            category = CaseCategory.REPAIRS_NONURGENT
        # Heuristic fallback if LLM gives little or no structure
        risk_flags = data.get("risk_flags") or []
        next_questions = data.get("next_questions") or []
        if not risk_flags:
            text = f"{request.issue} {request.free_text or ''}".lower()
            if any(token in text for token in ["urgent", "no hot water", "hot water", "gas leak", "electrical"]):
                risk_flags.append("urgent")
                if category == CaseCategory.REPAIRS_NONURGENT:
                    category = CaseCategory.REPAIRS_URGENT
        subcategory = data.get("subcategory") or request.answers.get("subcategory")
        return IntakeResult(
            category=category,
            subcategory=subcategory,
            risk_flags=risk_flags,
            next_questions=next_questions,
        )
