"""Quality assurance agent to validate drafted outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from llm import ChatMessage, LLMClient


@dataclass
class QAResult:
    status: str
    issues: List[str]

    @property
    def passed(self) -> bool:
        return self.status.lower() == "pass" and not self.issues


class QAAgent:
    """Use the LLM to check compliance for generated artefacts."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def run(self, body: str, citations: List[dict[str, str]]) -> QAResult:
        system_prompt = (
            "Validate that every rule has a citation, dates are correct, forms are named correctly, and tone is respectful."
            " Return JSON with status (pass|block) and issues[]. #agent:qa"
        )
        user_prompt = json.dumps({"body": body, "citations": citations})
        raw = self.llm.chat(
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ],
            temperature=0.0,
            response_format="json_object",
        )
        data = json.loads(raw)
        return QAResult(status=data.get("status", "pass"), issues=data.get("issues", []))
