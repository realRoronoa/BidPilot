"""Phase-2 follow-up tests: add-to-portfolio, portfolio PDF report, scenarios CRUD, capacity/suggest."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://qualification-ai.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def demo_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/demo-login", timeout=30)
    assert r.status_code == 200
    return s


# ---------------- Add-to-Portfolio ----------------
def test_to_opportunity_existing_returns_created_false(demo_session):
    r = demo_session.post(f"{API}/analyses/demo-analysis-0001/to-opportunity", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["created"] is False, f"expected created=false for linked seeded analysis, got {d}"
    assert d["opportunity"]["id"] == "opp-A"


def test_to_opportunity_new_analysis_flow_full(demo_session):
    """Create fresh analysis -> poll to completed -> to-opportunity created=true with AI_INFERRED resources.
    Cleanup: delete opportunity + analysis so demo remains 1/5."""
    body = {
        "tender_name": "TEST_ToOpp_Run",
        "tender_document_id": "demo-tender-doc-0001",
        "company_id": "demo-company-0001",
        "evidence_document_ids": [f"cd-{i}" for i in range(1, 8)],
    }
    r = demo_session.post(f"{API}/analyses", json=body, timeout=30)
    assert r.status_code == 200
    aid = r.json()["id"]
    opp_id = None
    try:
        deadline = time.time() + 200
        while time.time() < deadline:
            s = demo_session.get(f"{API}/analyses/{aid}/status", timeout=15).json()
            if s["status"] == "completed":
                break
            if s["status"] == "failed":
                pytest.fail(f"pipeline failed: {s.get('error')}")
            time.sleep(4)
        else:
            pytest.fail("analysis did not complete in time")

        r2 = demo_session.post(f"{API}/analyses/{aid}/to-opportunity", timeout=90)
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["created"] is True, f"expected created=true, got {d}"
        opp = d["opportunity"]
        opp_id = opp["id"]
        # AI_INFERRED sources
        srcs = opp.get("resource_sources") or {}
        assert srcs.get("estimators") == "AI_INFERRED"
        assert srcs.get("specialist_engineers") == "AI_INFERRED"
        assert srcs.get("capital_cr") == "AI_INFERRED"
        # resources populated with expected shape
        res = opp.get("resources") or {}
        for k in ("estimators", "specialist_engineers", "capital_cr"):
            assert k in res, f"missing resource {k}: {res}"
        # qualification_fit copied from decision
        assert isinstance(opp.get("qualification_fit"), (int, float))
        assert opp["qualification_fit"] > 0
        # verify persisted
        opps = demo_session.get(f"{API}/opportunities", timeout=15).json()
        assert any(o["id"] == opp_id for o in opps)

        # Second call should be idempotent (created=false)
        r3 = demo_session.post(f"{API}/analyses/{aid}/to-opportunity", timeout=30)
        assert r3.status_code == 200
        assert r3.json()["created"] is False
    finally:
        if opp_id:
            demo_session.delete(f"{API}/opportunities/{opp_id}", timeout=15)
        demo_session.delete(f"{API}/analyses/{aid}", timeout=15)

    # Assert demo hygiene: total analyses=1, opps=5
    stats = demo_session.get(f"{API}/dashboard", timeout=15).json()["stats"]
    assert stats["total"] == 1
    opps = demo_session.get(f"{API}/opportunities", timeout=15).json()
    assert len(opps) == 5
    assert {o["id"] for o in opps} == {"opp-A", "opp-B", "opp-C", "opp-D", "opp-E"}


# ---------------- Portfolio PDF report ----------------
def test_portfolio_report_pdf(demo_session):
    r = demo_session.get(f"{API}/portfolio/report", params={"objective": "value"}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 2048, f"pdf too small: {len(r.content)}"
    assert "attachment" in (r.headers.get("content-disposition") or "").lower()


def test_portfolio_report_requires_auth():
    r = requests.get(f"{API}/portfolio/report", timeout=15)
    assert r.status_code in (401, 403)


# ---------------- Scenarios CRUD ----------------
def test_scenarios_crud(demo_session):
    # create
    body = {"name": "TEST_scenario_specialist2", "objective": "value",
            "overrides": {"specialist_engineers": 2}}
    r = demo_session.post(f"{API}/portfolio/scenarios", json=body, timeout=15)
    assert r.status_code == 200, r.text
    sc = r.json()
    sid = sc["id"]
    assert sc["name"] == "TEST_scenario_specialist2"
    assert sc["overrides"] == {"specialist_engineers": 2}
    try:
        # list
        r2 = demo_session.get(f"{API}/portfolio/scenarios", timeout=15)
        assert r2.status_code == 200
        assert any(x["id"] == sid for x in r2.json())
    finally:
        # delete
        r3 = demo_session.delete(f"{API}/portfolio/scenarios/{sid}", timeout=15)
        assert r3.status_code == 200
        r4 = demo_session.get(f"{API}/portfolio/scenarios", timeout=15)
        assert not any(x["id"] == sid for x in r4.json())


# ---------------- Capacity suggest (AI) ----------------
def test_capacity_suggest_ai_inferred_not_persisted(demo_session):
    # Snapshot current capacity to verify no persistence
    before = demo_session.get(f"{API}/capacity", timeout=15).json()
    r = demo_session.post(f"{API}/capacity/suggest", timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("source") == "AI_INFERRED"
    sug = d.get("suggestion") or {}
    assert isinstance(sug.get("people"), dict) and sug["people"]
    assert isinstance(sug.get("equipment"), list)
    # Ensure not persisted
    after = demo_session.get(f"{API}/capacity", timeout=15).json()
    assert after["people"] == before["people"]
    assert after["equipment"] == before["equipment"]
    assert after["finance"] == before["finance"]
