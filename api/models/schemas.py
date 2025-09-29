"""Pydantic data models used by the FastAPI layer.

The schemas aim to mirror the product specification contained in the README.
They provide a typed surface for the HTTP routes while the in-memory
``CaseStore`` keeps temporary state during experimentation.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CaseCategory(str, Enum):
    """High level issue classifications supported by the MVP."""

    REPAIRS_URGENT = "repairs_urgent"
    REPAIRS_NONURGENT = "repairs_nonurgent"
    RENT_INCREASE = "rent_increase"
    NOTICE_TO_VACATE = "notice_to_vacate"
    BOND = "bond"
    MINIMUM_STANDARDS = "min_standards"
    ENTRY_RIGHTS = "entry_rights"


class CaseStatus(str, Enum):
    """Lifecycle states for a renter case."""

    INTAKE = "intake"
    COLLECTING_EVIDENCE = "collecting_evidence"
    LETTER_SENT = "letter_sent"
    AWAITING_RESPONSE = "awaiting_response"
    ESCALATE_RDRV = "escalate_RDRV"
    ESCALATE_VCAT = "escalate_VCAT"
    CLOSED = "closed"


class Renter(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    suburb: Optional[str] = None
    state: str = "VIC"
    postcode: Optional[str] = None


class RentalProvider(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    suburb: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
    agent_name: Optional[str] = None
    agent_email: Optional[str] = None
    agent_phone: Optional[str] = None


class Tenancy(BaseModel):
    renter_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None
    property_address: Optional[str] = None
    start_date: Optional[date] = None
    agreement_type: Optional[str] = None
    fixed_term_end: Optional[date] = None
    rent_amount_cents: Optional[int] = None
    rent_frequency: Optional[str] = None
    bond_amount_cents: Optional[int] = None


class IntakeRequest(BaseModel):
    renter: Renter
    provider: Optional[RentalProvider] = None
    tenancy: Optional[Tenancy] = None
    issue: str = Field(..., description="Primary issue description selected by the renter")
    free_text: Optional[str] = None
    answers: Dict[str, str] = Field(default_factory=dict)
    evidence_urls: List[str] = Field(default_factory=list)


class IntakeResponse(BaseModel):
    case_id: UUID
    category: CaseCategory
    subcategory: Optional[str] = None
    risk_flags: List[str] = Field(default_factory=list)
    next: str = Field("reason_and_draft", description="Next workflow step suggestion")
    next_questions: Optional[List[str]] = None


class LawCitation(BaseModel):
    url: str
    point: str
    as_of: date


class ReasoningStep(BaseModel):
    title: str
    description: str
    due_date: Optional[date] = None


class CaseReasoningResponse(BaseModel):
    explanation_plain: str
    steps: List[str]
    law_citations: List[LawCitation]
    deadlines: List[ReasoningStep]
    as_of_date: date


class DocumentReference(BaseModel):
    id: UUID
    type: str
    filename: str
    url: str
    created_at: datetime
    metadata: Dict[str, str] = Field(default_factory=dict)


class CaseTimelineEvent(BaseModel):
    label: str
    occurred_at: datetime
    metadata: Dict[str, str] = Field(default_factory=dict)


class CaseDetailResponse(BaseModel):
    case_id: UUID
    category: CaseCategory
    subcategory: Optional[str] = None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    critical_deadline: Optional[date] = None
    facts: Dict[str, str] = Field(default_factory=dict)
    law_citations: List[LawCitation] = Field(default_factory=list)
    recommendations: Dict[str, str] = Field(default_factory=dict)
    documents: List[DocumentReference] = Field(default_factory=list)
    events: List[CaseTimelineEvent] = Field(default_factory=list)


class DraftDocumentRequest(BaseModel):
    template: str
    channel: str = Field("docx", pattern="^(docx|pdf)$")


class DraftDocumentResponse(BaseModel):
    document_id: UUID
    urls: Dict[str, str]
    preview_subject: Optional[str] = None
    preview_body: Optional[str] = None


class EscalationTarget(str, Enum):
    RDRV = "RDRV"
    VCAT = "VCAT"


class EscalationRequest(BaseModel):
    target: EscalationTarget


class EscalationResponse(BaseModel):
    checklist: List[str]
    forms_list: List[str]
    fee_link: str
    draft_cover_letter_doc_id: Optional[UUID]


class LawSearchRequest(BaseModel):
    query: str
    top_k: int = 8


class LawSearchResult(BaseModel):
    source_url: str
    title: str
    snippet: str
    as_of_date: date


class LawSearchResponse(BaseModel):
    results: List[LawSearchResult]


class AskRequest(BaseModel):
    question: str
    top_k: int = 3


class AskResponse(BaseModel):
    answer: str
    citations: List[LawCitation]


class LawIngestRequest(BaseModel):
    url: str


class LawIngestResponse(BaseModel):
    added: bool
    result: LawSearchResult


__all__ = [
    "CaseCategory",
    "CaseStatus",
    "Renter",
    "RentalProvider",
    "Tenancy",
    "IntakeRequest",
    "IntakeResponse",
    "LawCitation",
    "CaseReasoningResponse",
    "DraftDocumentRequest",
    "DraftDocumentResponse",
    "EscalationRequest",
    "EscalationResponse",
    "LawSearchRequest",
    "LawSearchResponse",
    "CaseDetailResponse",
    "ReasoningStep",
    "LawIngestRequest",
    "LawIngestResponse",
    "AskRequest",
    "AskResponse",
]
