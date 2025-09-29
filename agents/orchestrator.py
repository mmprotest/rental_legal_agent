"""Coordinate agent calls for the API services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from api.models.schemas import CaseCategory, CaseReasoningResponse, IntakeRequest, LawSearchResponse
from agents.drafter import DraftResult, LetterDrafterAgent
from agents.intake import IntakeAgent, IntakeResult
from agents.law_retriever import LawRetrieverAgent, RetrievalContext
from agents.qa import QAAgent
from agents.reasoner import ReasonerAgent, ReasonerInput
from agents.scheduler import SchedulerAgent
from llm import LLMClient


@dataclass
class DraftPayload:
    template: str
    context: Dict[str, str]


class AgentOrchestrator:
    """Facilitate interactions across intake, reasoning, drafting, and QA."""

    def __init__(self) -> None:
        self.llm = LLMClient()
        self.intake_agent = IntakeAgent(self.llm)
        self.retriever = LawRetrieverAgent()
        self.reasoner = ReasonerAgent(self.llm)
        self.drafter = LetterDrafterAgent(self.llm)
        self.qa = QAAgent(self.llm)
        self.scheduler = SchedulerAgent()

    # Intake -------------------------------------------------------------
    def handle_intake(self, request: IntakeRequest) -> IntakeResult:
        return self.intake_agent.run(request)

    # Retrieval ----------------------------------------------------------
    def retrieve_law(
        self, query: str, category: CaseCategory | None = None, top_k: int = 8
    ) -> RetrievalContext:
        return self.retriever.retrieve(query=query, category=category, top_k=top_k)

    def search_law(self, query: str, top_k: int) -> LawSearchResponse:
        return self.retriever.search(query=query, top_k=top_k)

    # Reasoning ----------------------------------------------------------
    def reason(
        self, category: CaseCategory, facts: Dict[str, str], retrieval: RetrievalContext
    ) -> CaseReasoningResponse:
        law_payload = [
            {"title": result.title, "url": result.source_url, "summary": result.snippet, "as_of": str(result.as_of_date)}
            for result in retrieval.results
        ]
        reasoning_input = ReasonerInput(
            category=category,
            facts=facts,
            law_summaries=law_payload,
        )
        return self.reasoner.run(reasoning_input)

    # Drafting -----------------------------------------------------------
    def draft(self, payload: DraftPayload, citations: Dict[str, str]) -> DraftResult:
        context = dict(payload.context)
        context["citations"] = citations
        return self.drafter.run(payload.template, context)

    # QA -----------------------------------------------------------------
    def qa_check(self, draft: DraftResult, retrieval: RetrievalContext) -> bool:
        citations = [
            {"url": result.source_url, "title": result.title, "as_of": str(result.as_of_date)}
            for result in retrieval.results
        ]
        result = self.qa.run(draft.body, citations)
        return result.passed

    # Scheduler ----------------------------------------------------------
    def deadlines(self, category: CaseCategory):
        return self.scheduler.derive(category)


__all__ = ["AgentOrchestrator", "DraftPayload"]
