"""Document drafting agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Dict

from llm import ChatMessage, LLMClient


@dataclass
class DraftResult:
    subject: str
    body: str
    as_of: date


class LetterDrafterAgent:
    """Generate tailored letters using the LLM."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def run(self, template: str, context: Dict[str, str]) -> DraftResult:
        system_prompt = (
            "You draft legally accurate, respectful letters for Victorian rental matters."
            " Insert statutory timeframes and cite the provided law."
            " Respond with JSON containing subject and body fields. #agent:drafter"
        )
        user_prompt = json.dumps({"template": template, "context": context})
        raw = self.llm.chat(
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ],
            temperature=0.0,
            response_format="json_object",
        )
        data = json.loads(raw)
        return DraftResult(
            subject=data.get("subject", "Rental matter"),
            body=data.get("body", ""),
            as_of=date.today(),
        )
