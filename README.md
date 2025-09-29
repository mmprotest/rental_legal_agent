# rental_legal_agent

A privacy-first, multi-agent app that triages renter issues in Victoria, retrieves the right parts of the Residential Tenancies framework, explains options in plain English, and generates tailored letters/notices for rental providers or VCAT.

## Project layout

| Path | Description |
| --- | --- |
| `api/` | FastAPI application entrypoint and HTTP routes. |
| `api/models/` | Pydantic schemas that mirror the product data model. |
| `api/services/` | In-memory stores backed by the multi-agent orchestrator. |
| `agents/` | Agent implementations (intake, retriever, reasoner, drafter, QA, scheduler). |
| `core/` | Settings helpers for resolving environment configuration. |
| `knowledge/` | Curated legal snippets used for offline retrieval. |
| `llm/` | OpenAI-compatible chat client with HTTP and stub modes. |
| `static/` | Browser assets for the lightweight UI. |
| `templates/` | HTML template for the agent control panel. |
| `rag_indexer/` | Placeholder indexing pipeline for the legal corpus. |
| `scheduler/` | Deadline reminder scaffolding. |
| `tests/` | Pytest suite covering golden flows. |

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn api.main:app --reload
```

Run the test suite:

```bash
pytest
```

## API quickstart

After starting the FastAPI server you can exercise the golden path:

1. `POST /api/intake` to create a case.
2. `POST /api/case/{case_id}/reason` to run the reasoning agent.
3. `POST /api/case/{case_id}/draft` to draft a letter and persist it against the case.
4. `GET /api/case/{case_id}` to view artefacts, citations, and timeline events.
5. `POST /api/case/{case_id}/escalate` to review escalation checklists.
6. `POST /api/search-law` to query the curated Consumer Affairs Victoria corpus.

The default configuration operates entirely in-memory with deterministic stub
responses so tests run without network access. To call a live OpenAI-compatible
API, set `LLM_MODE=http` and supply `OPENAI_API_KEY`, `OPENAI_API_BASE`, and
optionally `OPENAI_MODEL`.

### Browser UI

Navigate to `http://localhost:8000/` to use the bundled UI. The page allows you
to run intake, reasoning, drafting, and case refresh actions without leaving the
browser. Static assets are served from the FastAPI application so no additional
build tooling is required.
