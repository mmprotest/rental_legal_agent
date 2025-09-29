"""Generic OpenAI-compatible chat client with stubbed fallback."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable, List, Optional
import re

from core.settings import get_settings


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class StubbedResponse:
    content: str
    reasoning: Optional[str] = None


class LLMClient:
    """Thin wrapper around an OpenAI-compatible chat completion endpoint."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._mode = self.settings.resolved_llm_mode
        self._http_opener = urllib.request.build_opener()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat(
        self,
        messages: Iterable[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 800,
        response_format: Optional[str] = None,
    ) -> str:
        if self._mode == "stub":
            return self._chat_stub(messages)
        return self._chat_http(messages, temperature, max_tokens, response_format)

    # ------------------------------------------------------------------
    # HTTP mode
    # ------------------------------------------------------------------
    def _chat_http(
        self,
        messages: Iterable[ChatMessage],
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
    ) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY must be set for HTTP mode")
        payload: dict[str, object] = {
            "model": self.settings.openai_model,
            "messages": [message.__dict__ for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # Avoid provider-specific response_format requirements; rely on prompt formatting
        base_url = self.settings.openai_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with self._http_opener.open(request, timeout=60.0) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # pragma: no cover - network mode only
            message = exc.read().decode("utf-8") if exc.fp else exc.reason
            raise RuntimeError(f"LLM HTTP error: {message}") from exc
        data = json.loads(raw)
        return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # Stub mode
    # ------------------------------------------------------------------
    def _chat_stub(self, messages: Iterable[ChatMessage]) -> str:
        """Return deterministic responses for automated tests."""

        history: List[ChatMessage] = list(messages)
        system = history[0].content if history else ""
        user = history[-1].content if history else ""
        if "#agent:intake" in system:
            return json.dumps(
                {
                    "category": "repairs_urgent" if "urgent" in user.lower() else "repairs_nonurgent",
                    "subcategory": "hot_water_out" if "hot water" in user.lower() else None,
                    "risk_flags": ["urgent"] if "urgent" in user.lower() or "hot water" in user.lower() else [],
                    "next_questions": [],
                }
            )
        if "#agent:reasoner" in system:
            return json.dumps(
                {
                    "explanation": "No hot water counts as an urgent repair in Victoria. The rental provider must organise repairs immediately and reimburse any emergency work within 7 days.",
                    "steps": [
                        "Send an urgent repair request referencing the Consumer Affairs Victoria guidance.",
                        "If there is no action within 24 hours, arrange repairs up to $2,500 and keep receipts.",
                        "Request reimbursement and escalate to RDRV then VCAT if unpaid after 7 days.",
                    ],
                    "deadlines": [
                        {
                            "title": "Follow up urgent repair",
                            "description": "Confirm the rental provider has arranged immediate attendance.",
                            "due_in_days": 1,
                        },
                        {
                            "title": "Reimbursement due",
                            "description": "Ensure reimbursement is received within 7 days of invoices.",
                            "due_in_days": 7,
                        },
                    ],
                    "citations": [
                        {
                            "url": "https://www.consumer.vic.gov.au/housing/renting/repairs-alterations-safety-and-pets/repairs/repairs-in-rental-properties",
                            "point": "Urgent repairs must be actioned immediately; renters can spend up to $2,500 and be repaid within 7 days.",
                            "as_of": "2025-05-02",
                        }
                    ],
                }
            )
        if "#agent:drafter" in system:
            return json.dumps(
                {
                    "subject": "Urgent repair request for heating",
                    "body": "I am writing to request urgent repairs for the loss of hot water at the property. Under Consumer Affairs Victoria guidance, urgent repairs must be arranged immediately. If I do not hear from you within 24 hours I will arrange repairs up to $2,500 and expect reimbursement within 7 days, with escalation to RDRV or VCAT if required.",
                }
            )
        if "#agent:qa" in system:
            return json.dumps(
                {
                    "status": "pass",
                    "issues": [],
                }
            )
        if "#agent:summary" in system:
            return "Case updated"
        return json.dumps({"message": "stub response"})


def safe_json_loads(raw: str) -> dict:
    """Parse loosely formatted JSON from LLM output.

    - Strips markdown code fences
    - Extracts the first top-level JSON object if extra text surrounds it
    - Falls back to empty dict on failure
    """
    text = raw.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        # remove opening fence
        text = re.sub(r"^```[a-zA-Z0-9_\-]*\n", "", text)
        # remove closing fence
        text = re.sub(r"\n```\s*$", "", text)
    # Quick path
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to find a JSON object substring
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return {}


__all__ = ["ChatMessage", "LLMClient", "StubbedResponse", "safe_json_loads"]
