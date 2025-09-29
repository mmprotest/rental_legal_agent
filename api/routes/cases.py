"""HTTP routes for interacting with renter cases.

The handlers orchestrate against the ``CaseStore`` which stands in for the
future persistence and agent pipeline. Each route mirrors an endpoint described
in the product specification so the frontend team can develop against a stable
contract.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.models.schemas import (
    CaseDetailResponse,
    CaseReasoningResponse,
    DraftDocumentRequest,
    DraftDocumentResponse,
    EscalationRequest,
    EscalationResponse,
    IntakeRequest,
    IntakeResponse,
    LawSearchRequest,
    LawSearchResponse,
    LawIngestRequest,
    LawIngestResponse,
)
from api.services.case_store import case_store

router = APIRouter(prefix="/api", tags=["cases"])


@router.post("/intake", response_model=IntakeResponse)
def create_case(request: IntakeRequest) -> IntakeResponse:
    """Create a case from renter intake answers."""

    return case_store.create_case(request)


@router.post("/case/{case_id}/reason", response_model=CaseReasoningResponse)
def reason_case(case_id: str) -> CaseReasoningResponse:
    """Return the reasoning artefacts for a case."""

    try:
        return case_store.get_reasoning(_parse_uuid(case_id))
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/case/{case_id}/draft", response_model=DraftDocumentResponse)
def draft_document(case_id: str, request: DraftDocumentRequest) -> DraftDocumentResponse:
    """Generate a placeholder letter or document for a case."""

    try:
        return case_store.create_document(_parse_uuid(case_id), request.template, request.channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/case/{case_id}", response_model=CaseDetailResponse)
def get_case(case_id: str) -> CaseDetailResponse:
    """Return the canonical representation of a case."""

    try:
        return case_store.get_case(_parse_uuid(case_id))
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/case/{case_id}/escalate", response_model=EscalationResponse)
def escalate_case(case_id: str, request: EscalationRequest) -> EscalationResponse:
    """Return checklists and links for escalating a case."""

    try:
        return case_store.escalate(_parse_uuid(case_id), request.target.value)
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/search-law", response_model=LawSearchResponse)
def search_law(request: LawSearchRequest) -> LawSearchResponse:
    """Perform a placeholder legal search across the staged corpus."""

    return case_store.search_law(request.query, request.top_k)


@router.post("/ingest-law", response_model=LawIngestResponse)
def ingest_law(request: LawIngestRequest) -> LawIngestResponse:
    """Fetch a URL and add it to the in-memory law corpus at runtime."""

    return case_store.ingest_law(request.url)


def _parse_uuid(value: str):
    from uuid import UUID

    return UUID(value)

