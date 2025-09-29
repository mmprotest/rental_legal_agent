"""FastAPI application entrypoint for the rental legal agent API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from api.routes.cases import router as cases_router

app = FastAPI(
    title="Rental Legal Navigator",
    version="0.1.0",
    description=(
        "APIs for triaging Victorian renter issues, retrieving relevant law, and "
        "drafting tailored correspondence."
    ),
)

app.include_router(cases_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Simple readiness probe used by deployment tooling."""

    return {"status": "ok"}


@app.get("/", response_model=None)
def index() -> str:
    """Serve the interactive UI front-end."""

    html_path = Path("templates/index.html")
    if not html_path.exists():  # pragma: no cover - safety guard
        raise HTTPException(status_code=404, detail="UI template missing")
    return html_path.read_text(encoding="utf-8")


@app.get("/static/{asset}", response_model=None)
def static_asset(asset: str) -> str:
    """Serve static assets like the UI JavaScript."""

    file_path = Path("static") / asset
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Static asset not found")
    return file_path.read_text(encoding="utf-8")

