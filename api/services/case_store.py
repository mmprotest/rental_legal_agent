"""In-memory state containers used during early prototyping.

The production architecture will persist to PostgreSQL + pgvector, but the
store objects let us exercise the HTTP flows and reason about the multi-agent
interactions without a database dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
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
    AskResponse,
    LawCitation,
    LawSearchResponse,
    ReasoningStep,
)
from llm import ChatMessage, LLMClient, safe_json_loads


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
    # General legal Q&A
    # ------------------------------------------------------------------
    def ask(self, question: str, top_k: int) -> AskResponse:
        text = (question or "").lower()
        # Safety: prohibit violence and advise lawful steps (generic)
        if any(term in text for term in ["hurt", "harm", "violence", "attack", "kill", "assault"]):
            safety_answer = (
                "You must not harm anyone. Violence is illegal. Use lawful options: document the issue, try to resolve directly if safe, "
                "seek help from your rental provider/agent if relevant, and contact the appropriate authority (e.g., Consumer Affairs Victoria, council, or police) depending on the problem."
            )
            retrieval = self.agents.retrieve_law(query=question, top_k=top_k)
            citations = [
                LawCitation(url=r.source_url, point=r.snippet.split(".")[0].strip(), as_of=r.as_of_date)
                for r in retrieval.results[:3]
            ]
            return AskResponse(answer=safety_answer, citations=citations)

        # Semantic retrieval
        retrieval = self.agents.retrieve_law(query=question, top_k=max(6, top_k))
        # Prefer results with token overlap to reduce generic answers
        q_tokens = {t for t in (question or "").lower().split() if len(t) > 2}
        filtered = [r for r in retrieval.results if any(tok in r.title.lower() or tok in r.snippet.lower() for tok in q_tokens)]
        ranked = filtered if filtered else retrieval.results
        law_payload = [
            {"id": i + 1, "title": r.title, "url": r.source_url, "summary": r.snippet, "as_of": str(r.as_of_date)}
            for i, r in enumerate(ranked[:6])
        ]
        # Direct ask chain (bypass category enums)
        llm = LLMClient()
        system_prompt = (
            "You are a Victorian renting law assistant. Answer the user's question in plain English using ONLY the provided law summaries. "
            "Do not include unrelated topics. Be specific and practical. "
            "Respond ONLY as JSON with keys: answer (string), citations (array of {url, point, as_of})."
        )
        user_prompt = {
            "question": question,
            "law": law_payload,
            "requirements": {
                "jurisdiction": "Victoria, Australia",
                "citations_required": True,
                "no_extra_prose": True,
            },
        }
        raw = llm.chat([
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=json.dumps(user_prompt)),
        ], temperature=0.2)
        data = safe_json_loads(raw)
        answer = data.get("answer") or ""
        cit_payload = data.get("citations") or []
        citations: List[LawCitation] = []
        for c in cit_payload:
            try:
                citations.append(
                    LawCitation(
                        url=c.get("url", ""),
                        point=c.get("point", ""),
                        as_of=date.fromisoformat(c.get("as_of", str(date.today()))),
                    )
                )
            except Exception:
                continue
        # If model returned nothing useful, synthesize from retrieval
        if not answer:
            answer = " ".join([item["summary"] for item in law_payload[:2]])[:800]
        if not citations:
            citations = [
                LawCitation(url=r.source_url, point=r.snippet.split(".")[0].strip(), as_of=r.as_of_date)
                for r in retrieval.results[:3]
            ]
        return AskResponse(answer=answer, citations=citations)

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


