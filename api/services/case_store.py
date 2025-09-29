"""In-memory state containers used during early prototyping.

The production architecture will persist to PostgreSQL + pgvector, but the
store objects let us exercise the HTTP flows and reason about the multi-agent
interactions without a database dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, List, Optional
from urllib.request import urlopen
from urllib.error import URLError
from uuid import UUID, uuid4

from agents.orchestrator import AgentOrchestrator, DraftPayload
from api.models.schemas import (
    CaseCategory,
    CaseDetailResponse,
    CaseReasoningResponse,
    CaseStatus,
    CaseTimelineEvent,
    DocumentReference,
    DraftDocumentResponse,
    EscalationResponse,
    IntakeRequest,
    IntakeResponse,
    LawIngestResponse,
    LawCitation,
    LawSearchResponse,
    ReasoningStep,
)


@dataclass
class CaseRecord:
    """Internal representation of a case."""

    id: UUID
    category: CaseCategory
    subcategory: Optional[str]
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    renter: Dict[str, str]
    provider: Dict[str, str]
    facts: Dict[str, str] = field(default_factory=dict)
    risk_flags: List[str] = field(default_factory=list)
    critical_deadline: Optional[date] = None
    law_citations: List[LawCitation] = field(default_factory=list)
    recommendations: Dict[str, str] = field(default_factory=dict)
    documents: List[DocumentReference] = field(default_factory=list)
    events: List[CaseTimelineEvent] = field(default_factory=list)


class CaseStore:
    """Simple mutable case repository."""

    def __init__(self) -> None:
        self._cases: Dict[UUID, CaseRecord] = {}
        self.agents = AgentOrchestrator()

    # ------------------------------------------------------------------
    # Intake
    # ------------------------------------------------------------------
    def create_case(self, payload: IntakeRequest) -> IntakeResponse:
        case_id = uuid4()
        intake = self.agents.handle_intake(payload)
        category = intake.category
        now = datetime.now(timezone.utc)
        record = CaseRecord(
            id=case_id,
            category=category,
            subcategory=intake.subcategory or self._derive_subcategory(payload),
            status=CaseStatus.INTAKE,
            created_at=now,
            updated_at=now,
            renter=payload.renter.model_dump(),
            provider=payload.provider.model_dump() if payload.provider else {},
            facts={"issue": payload.issue, **payload.answers},
            risk_flags=intake.risk_flags,
        )
        deadlines = self.agents.deadlines(category)
        record.critical_deadline = deadlines.deadlines[0].due_date if deadlines.deadlines else None
        record.events.append(
            CaseTimelineEvent(
                label="Case created",
                occurred_at=now,
                metadata={"category": category.value},
            )
        )
        self._cases[case_id] = record
        return IntakeResponse(
            case_id=case_id,
            category=record.category,
            subcategory=record.subcategory,
            risk_flags=record.risk_flags,
            next_questions=intake.next_questions or None,
        )

    # ------------------------------------------------------------------
    # Case reasoning
    # ------------------------------------------------------------------
    def get_reasoning(self, case_id: UUID) -> CaseReasoningResponse:
        record = self._cases[case_id]
        retrieval = self.agents.retrieve_law(
            query=record.facts.get("issue", ""), category=record.category, top_k=3
        )
        reasoning = self.agents.reason(record.category, record.facts, retrieval)
        record.law_citations = reasoning.law_citations
        record.recommendations = {
            "summary": reasoning.explanation_plain,
        }
        record.updated_at = datetime.now(timezone.utc)
        record.events.append(
            CaseTimelineEvent(
                label="Reasoning generated",
                occurred_at=record.updated_at,
                metadata={"step_count": str(len(reasoning.steps))},
            )
        )
        return reasoning

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    def create_document(self, case_id: UUID, template: str, channel: str) -> DraftDocumentResponse:
        record = self._cases[case_id]
        retrieval = self.agents.retrieve_law(
            query=f"{template} {record.facts.get('issue', '')}",
            category=record.category,
            top_k=3,
        )
        payload = DraftPayload(
            template=template,
            context={
                "renter_name": record.renter.get("full_name", ""),
                "provider_name": record.provider.get("name", "Rental Provider"),
                "issue": record.facts.get("issue", ""),
            },
        )
        citations = {"primary_url": retrieval.results[0].source_url if retrieval.results else ""}
        draft = self.agents.draft(payload, citations)
        qa_result = self.agents.qa_check(draft, retrieval)
        doc_id = uuid4()
        now = datetime.now(timezone.utc)
        filename = f"{template}-{doc_id}.{channel}"
        doc = DocumentReference(
            id=doc_id,
            type=template,
            filename=filename,
            url=f"https://example.invalid/docs/{filename}",
            created_at=now,
            metadata={
                "subject": draft.subject,
                "body": draft.body,
                "channel": channel,
                "qa_status": getattr(qa_result, "status", "unknown"),
                "qa_issues": ", ".join(getattr(qa_result, "issues", [])),
            },
        )
        record.documents.append(doc)
        record.updated_at = now
        record.events.append(
            CaseTimelineEvent(
                label="Draft generated",
                occurred_at=now,
                metadata={
                    "document_id": str(doc_id),
                    "template": template,
                    "qa_status": getattr(qa_result, "status", "unknown"),
                },
            )
        )
        return DraftDocumentResponse(
            document_id=doc_id,
            urls={channel: doc.url},
            preview_subject=draft.subject,
            preview_body=draft.body,
        )

    # ------------------------------------------------------------------
    # Case retrieval
    # ------------------------------------------------------------------
    def get_case(self, case_id: UUID) -> CaseDetailResponse:
        record = self._cases[case_id]
        return CaseDetailResponse(
            case_id=record.id,
            category=record.category,
            subcategory=record.subcategory,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            critical_deadline=record.critical_deadline,
            facts=record.facts,
            law_citations=record.law_citations,
            recommendations=record.recommendations,
            documents=record.documents,
            events=record.events,
        )

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------
    def escalate(self, case_id: UUID, target: str) -> EscalationResponse:
        record = self._cases[case_id]
        record.updated_at = datetime.now(timezone.utc)
        checklist = [
            "Review all communications and evidence gathered so far.",
            "Prepare supporting documents such as invoices, notices, and photographs.",
            "Confirm the statutory timelines are still open before submitting.",
        ]
        forms = [
            "RDRV repair dispute form" if target == "RDRV" else "VCAT rental application form",
        ]
        fee_link = "https://www.vcat.vic.gov.au/fees"
        record.events.append(
            CaseTimelineEvent(
                label="Escalation guidance",
                occurred_at=datetime.now(timezone.utc),
                metadata={"target": target},
            )
        )
        return EscalationResponse(
            checklist=checklist,
            forms_list=forms,
            fee_link=fee_link,
            draft_cover_letter_doc_id=None,
        )

    # ------------------------------------------------------------------
    # Law search
    # ------------------------------------------------------------------
    def search_law(self, query: str, top_k: int) -> LawSearchResponse:
        return self.agents.search_law(query=query, top_k=top_k)

    # ------------------------------------------------------------------
    # Law ingestion (runtime)
    # ------------------------------------------------------------------
    def ingest_law(self, url: str) -> LawIngestResponse:
        """Fetch a URL and add to the retriever's runtime corpus with naive extraction."""
        try:
            with urlopen(url, timeout=10) as resp:
                content_bytes = resp.read()
        except URLError as exc:
            raise ValueError(f"Failed to fetch URL: {exc}") from exc
        content = content_bytes.decode("utf-8", errors="ignore")
        title = _extract_between(content, "<title>", "</title>") or url
        # Crude summary: first 400 non-whitespace characters of text content
        summary = " ".join(content.split())[:400]
        # Naive keywords from title
        keywords = [token.lower() for token in title.split() if len(token) > 3][:8]
        from datetime import date
        from api.models.schemas import LawSearchResult

        result = LawSearchResult(source_url=url, title=title, snippet=summary, as_of_date=date.today())
        # Register with retriever's runtime index
        self.agents.retriever.add_runtime(result, keywords)
        return LawIngestResponse(added=True, result=result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _derive_subcategory(self, payload: IntakeRequest) -> Optional[str]:
        return payload.answers.get("subcategory")


case_store = CaseStore()
"""Module-level singleton used by the API routes."""


def _extract_between(text: str, start: str, end: str) -> Optional[str]:
    try:
        i = text.index(start)
        j = text.index(end, i + len(start))
        return text[i + len(start) : j]
    except ValueError:
        return None


