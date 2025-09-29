from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ui_assets_served() -> None:
    html_response = client.get("/")
    assert html_response.status_code == 200
    assert "Rental Legal Navigator" in html_response.json()

    js_response = client.get("/static/app.js")
    assert js_response.status_code == 200
    assert "intakeForm" in js_response.json()


def test_intake_reasoning_flow() -> None:
    intake_payload = {
        "renter": {"full_name": "Ada Tenant"},
        "issue": "urgent repairs - no hot water",
        "answers": {"subcategory": "hot_water_out"},
        "evidence_urls": ["https://example.invalid/photo.jpg"],
    }
    intake_response = client.post("/api/intake", json=intake_payload)
    assert intake_response.status_code == 200
    body = intake_response.json()
    case_id = body["case_id"]
    assert body["category"] == "repairs_urgent"
    assert "urgent" in body["risk_flags"]

    reasoning_response = client.post(f"/api/case/{case_id}/reason")
    assert reasoning_response.status_code == 200
    reasoning = reasoning_response.json()
    assert len(reasoning["law_citations"]) >= 1
    assert any("repairs" in citation["url"] for citation in reasoning["law_citations"])

    draft_response = client.post(
        f"/api/case/{case_id}/draft",
        json={"template": "repairs_urgent", "channel": "docx"},
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["urls"]["docx"].startswith("https://example.invalid")

    case_response = client.get(f"/api/case/{case_id}")
    assert case_response.status_code == 200
    case_body = case_response.json()
    assert case_body["documents"], "expected stored document reference"
    assert case_body["documents"][0]["metadata"]["body"]
    assert any(event["label"] == "Reasoning generated" for event in case_body["events"])

    escalation_response = client.post(
        f"/api/case/{case_id}/escalate", json={"target": "RDRV"}
    )
    assert escalation_response.status_code == 200
    escalation = escalation_response.json()
    assert "RDRV" in escalation["forms_list"][0]

    refreshed_case = client.get(f"/api/case/{case_id}").json()
    assert any(event["label"] == "Escalation guidance" for event in refreshed_case["events"])

    law_search_response = client.post(
        "/api/search-law", json={"query": "urgent repairs", "top_k": 2}
    )
    assert law_search_response.status_code == 200
    results = law_search_response.json()["results"]
    assert len(results) == 2
    assert any("repairs" in result["title"].lower() for result in results)

