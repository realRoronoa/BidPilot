"""BidPilot backend end-to-end tests.
Uses REACT_APP_BACKEND_URL and cookie-based auth (httpOnly cookies).
"""
import io
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://qualification-ai.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@bidpilot.io")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo1234")


# --------------- Fixtures ---------------
@pytest.fixture(scope="session")
def demo_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/demo-login", timeout=30)
    assert r.status_code == 200, f"demo-login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == DEMO_EMAIL
    assert data["name"] == "Ravi Menon"
    assert data["role"] == "Owner"
    return s


@pytest.fixture(scope="session")
def new_user_session():
    s = requests.Session()
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/signup", json={
        "name": "Test User", "email": email, "password": "testpass123",
        "company_name": "TEST_Company"
    }, timeout=30)
    assert r.status_code == 200, f"signup failed: {r.text}"
    s._email = email  # attach for later
    return s


# --------------- Health & Auth ---------------
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_demo_login_and_me(demo_session):
    r = demo_session.get(f"{API}/auth/me", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["email"] == DEMO_EMAIL
    assert d["workspace_id"] == "demo-ws-0001"


def test_signup_and_login(new_user_session):
    email = new_user_session._email
    # Test login with same creds in a fresh session
    s2 = requests.Session()
    r = s2.post(f"{API}/auth/login", json={"email": email, "password": "testpass123"}, timeout=30)
    assert r.status_code == 200
    me = s2.get(f"{API}/auth/me", timeout=15)
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_brute_force_lockout():
    """5+ wrong passwords should trigger 429."""
    s = requests.Session()
    email = f"bf_{uuid.uuid4().hex[:6]}@example.com"
    # create the account first
    r = s.post(f"{API}/auth/signup", json={
        "name": "BF User", "email": email, "password": "correctpass"
    }, timeout=30)
    assert r.status_code == 200
    s2 = requests.Session()
    codes = []
    for _ in range(7):
        r = s2.post(f"{API}/auth/login", json={"email": email, "password": "wrong"}, timeout=15)
        codes.append(r.status_code)
    # should include at least one 429 within 7 attempts
    assert 429 in codes, f"expected 429 lockout, got {codes}"


def test_logout(demo_session):
    s = requests.Session()
    s.post(f"{API}/auth/demo-login", timeout=15)
    r = s.post(f"{API}/auth/logout", timeout=15)
    assert r.status_code == 200
    r2 = s.get(f"{API}/auth/me", timeout=15)
    assert r2.status_code in (401, 403)


# --------------- Dashboard ---------------
def test_dashboard(demo_session):
    r = demo_session.get(f"{API}/dashboard", timeout=15)
    assert r.status_code == 200
    d = r.json()
    stats = d["stats"]
    assert stats["total"] == 1
    assert stats["conditional"] == 1
    assert stats["open_actions"] > 0
    assert isinstance(d["recent_analyses"], list) and len(d["recent_analyses"]) >= 1
    assert isinstance(d["deadlines"], list)
    assert isinstance(d["activity"], list)


# --------------- Seeded Analysis ---------------
def test_list_analyses(demo_session):
    r = demo_session.get(f"{API}/analyses", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == "demo-analysis-0001"
    assert data[0]["decision"] == "BID WITH CONDITIONS"
    assert data[0]["readiness"] == 76


def test_get_seeded_analysis(demo_session):
    r = demo_session.get(f"{API}/analyses/demo-analysis-0001", timeout=15)
    assert r.status_code == 200
    a = r.json()
    assert a["status"] == "completed"
    assert a["decision"]["outcome"] == "BID WITH CONDITIONS"
    assert a["decision"]["readiness_score"] == 76


def test_seeded_findings(demo_session):
    aid = "demo-analysis-0001"
    reqs = demo_session.get(f"{API}/analyses/{aid}/requirements", timeout=15).json()
    assert len(reqs) >= 5
    # FAIL for Similar completed projects
    fail_similar = [r for r in reqs if r["status"] == "FAIL" and "similar" in r["name"].lower()]
    assert fail_similar, f"expected FAIL for Similar completed projects; got: {[(r['name'], r['status']) for r in reqs]}"
    # NEEDS_REVIEW for ISO 9001
    iso = [r for r in reqs if "iso 9001" in r["name"].lower()]
    assert iso and iso[0]["status"] in ("NEEDS_REVIEW", "NEEDS REVIEW"), f"ISO 9001 status: {iso}"

    for ep in ("eligibility", "compliance", "technical", "risks"):
        rr = demo_session.get(f"{API}/analyses/{aid}/{ep}", timeout=15)
        assert rr.status_code == 200, f"{ep}: {rr.status_code}"


def test_evidence_traceability(demo_session):
    aid = "demo-analysis-0001"
    reqs = demo_session.get(f"{API}/analyses/{aid}/requirements", timeout=15).json()
    # pick a requirement with evidence_source_document
    target = next((r for r in reqs if r.get("evidence_source_document")), reqs[0])
    r = demo_session.get(f"{API}/analyses/{aid}/evidence/{target['id']}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "requirement" in d and "tender" in d and "company" in d
    # tender page text should exist for the requirement
    assert d["tender"]["page"] is not None
    # requirement includes explanation/evidence
    assert d["requirement"].get("explanation") or d["requirement"].get("company_evidence")


# --------------- Action items ---------------
def test_action_toggle_persists(demo_session):
    items = demo_session.get(f"{API}/analyses/demo-analysis-0001/action-items", timeout=15).json()
    assert items, "no action items seeded"
    item = items[0]
    original = item["status"]
    new_status = "DONE" if original == "OPEN" else "OPEN"
    r = demo_session.patch(f"{API}/action-items/{item['id']}", json={"status": new_status}, timeout=15)
    assert r.status_code == 200
    # verify persisted
    items2 = demo_session.get(f"{API}/analyses/demo-analysis-0001/action-items", timeout=15).json()
    found = next(i for i in items2 if i["id"] == item["id"])
    assert found["status"] == new_status
    # revert
    demo_session.patch(f"{API}/action-items/{item['id']}", json={"status": original}, timeout=15)


# --------------- Documents ---------------
def test_documents_list(demo_session):
    r = demo_session.get(f"{API}/documents", params={"doc_type": "company"}, timeout=15)
    assert r.status_code == 200
    docs = r.json()
    assert len(docs) == 7, f"expected 7 seeded company docs, got {len(docs)}"


def _make_pdf_bytes():
    """Tiny valid single-page PDF."""
    # minimal PDF
    return (b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj\n"
            b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 720 Td (TEST_upload) Tj ET\nendstream\nendobj\n"
            b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n0000000098 00000 n \n0000000210 00000 n \ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n295\n%%EOF")


def test_document_upload_and_delete(demo_session):
    pdf = _make_pdf_bytes()
    files = {"file": ("TEST_upload.pdf", pdf, "application/pdf")}
    data = {"doc_type": "company", "category": "Other"}
    r = demo_session.post(f"{API}/documents", files=files, data=data, timeout=60)
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text}"
    doc = r.json()
    assert doc["filename"] == "TEST_upload.pdf"
    assert isinstance(doc.get("page_count"), int)
    did = doc["id"]
    # delete
    r2 = demo_session.delete(f"{API}/documents/{did}", timeout=15)
    assert r2.status_code == 200


# --------------- Company ---------------
def test_company(demo_session):
    r = demo_session.get(f"{API}/company", timeout=15)
    assert r.status_code == 200
    c = r.json()
    assert "ABC Infrastructure" in c["legal_name"]
    assert isinstance(c.get("projects"), list) and c["projects"]
    assert isinstance(c.get("personnel"), list) and c["personnel"]
    assert isinstance(c.get("equipment"), list) and c["equipment"]

    # patch
    body = {"legal_name": c["legal_name"], "registration": c.get("registration", ""),
            "location": "Bengaluru, KA (updated)", "years_experience": c.get("years_experience", 0),
            "turnover": c.get("turnover", ""), "specialization": c.get("specialization", "")}
    r2 = demo_session.patch(f"{API}/company/{c['id']}", json=body, timeout=15)
    assert r2.status_code == 200
    assert r2.json()["location"] == "Bengaluru, KA (updated)"


# --------------- Notifications ---------------
def test_notifications(demo_session):
    r = demo_session.get(f"{API}/notifications", timeout=15)
    assert r.status_code == 200
    notifs = r.json()
    assert len(notifs) >= 3
    nid = notifs[0]["id"]
    r2 = demo_session.patch(f"{API}/notifications/{nid}", timeout=15)
    assert r2.status_code == 200
    r3 = demo_session.post(f"{API}/notifications/read-all", timeout=15)
    assert r3.status_code == 200


# --------------- Billing ---------------
def test_billing(demo_session):
    r = demo_session.get(f"{API}/billing", timeout=15)
    assert r.status_code == 200
    b = r.json()
    assert b["subscription"]["plan_name"] == "Professional"
    assert b["usage"] is not None
    assert len(b["plans"]) == 3
    assert isinstance(b["invoices"], list)
    assert b.get("sandbox") is True
    # upgrade
    plan_id = b["plans"][0]["id"]
    r2 = demo_session.post(f"{API}/billing/upgrade", json={"plan_id": plan_id}, timeout=15)
    assert r2.status_code == 200
    j = r2.json()
    assert j.get("sandbox") is True
    assert "sandbox" in (j.get("message") or "").lower()
    # revert to Professional
    prof = next(p for p in b["plans"] if p["name"] == "Professional")
    demo_session.post(f"{API}/billing/upgrade", json={"plan_id": prof["id"]}, timeout=15)


# --------------- Users ---------------
def test_users_invite_role(demo_session):
    members_before = demo_session.get(f"{API}/workspace/users", timeout=15).json()
    email = f"invitee_{uuid.uuid4().hex[:6]}@example.com"
    r = demo_session.post(f"{API}/workspace/users/invite", json={
        "name": "TEST_Invitee", "email": email, "role": "Member"
    }, timeout=15)
    assert r.status_code == 200
    m = r.json()
    assert m["status"] == "Invited"
    # patch role
    r2 = demo_session.patch(f"{API}/workspace/users/{m['id']}", json={"role": "Reviewer"}, timeout=15)
    assert r2.status_code == 200
    members_after = demo_session.get(f"{API}/workspace/users", timeout=15).json()
    assert len(members_after) == len(members_before) + 1
    found = next(x for x in members_after if x["id"] == m["id"])
    assert found["role"] == "Reviewer"


# --------------- Workspace isolation ---------------
def test_workspace_isolation(new_user_session):
    # New user must not see demo analyses
    r = new_user_session.get(f"{API}/analyses", timeout=15)
    assert r.status_code == 200
    assert r.json() == []
    # Nor demo docs
    r2 = new_user_session.get(f"{API}/documents", timeout=15)
    assert r2.status_code == 200
    assert all(d["id"] not in {"demo-tender-doc-0001"} for d in r2.json())
    # Should NOT be able to fetch demo analysis
    r3 = new_user_session.get(f"{API}/analyses/demo-analysis-0001", timeout=15)
    assert r3.status_code == 404


# --------------- Real AI pipeline ---------------
def test_real_analysis_pipeline(demo_session):
    """Run the full analysis on the seeded tender doc via Claude and confirm all 9 stages complete."""
    body = {
        "tender_name": "TEST_Real_Run",
        "tender_document_id": "demo-tender-doc-0001",
        "company_id": "demo-company-0001",
        "evidence_document_ids": [f"cd-{i}" for i in range(1, 8)],
    }
    r = demo_session.post(f"{API}/analyses", json=body, timeout=30)
    assert r.status_code == 200, r.text
    aid = r.json()["id"]

    try:
        deadline = time.time() + 180  # up to 3 minutes
        final = None
        while time.time() < deadline:
            s = demo_session.get(f"{API}/analyses/{aid}/status", timeout=15).json()
            if s["status"] == "completed":
                final = s
                break
            if s["status"] == "failed":
                pytest.fail(f"pipeline failed: {s.get('error')}")
            time.sleep(4)
        assert final is not None, "analysis did not complete in time"
        assert len(final.get("stages", [])) == 9

        # decision + requirements populated
        a = demo_session.get(f"{API}/analyses/{aid}", timeout=15).json()
        assert a["decision"] is not None
        assert a["decision"]["outcome"] in ("BID", "BID WITH CONDITIONS", "NO-BID")
        reqs = demo_session.get(f"{API}/analyses/{aid}/requirements", timeout=15).json()
        assert len(reqs) >= 3
    finally:
        # cleanup
        demo_session.delete(f"{API}/analyses/{aid}", timeout=15)

    # Final: demo dashboard total should remain 1
    stats = demo_session.get(f"{API}/dashboard", timeout=15).json()["stats"]
    assert stats["total"] == 1



# --------------- New Features (iteration 2) ---------------

# Report: server-side branded PDF download
def test_report_download_seeded(demo_session):
    r = demo_session.get(f"{API}/analyses/demo-analysis-0001/report", timeout=30)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 3000, f"pdf too small: {len(r.content)}"
    assert "attachment" in (r.headers.get("content-disposition") or "").lower()


def test_report_requires_auth():
    r = requests.get(f"{API}/analyses/demo-analysis-0001/report", timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403 no-cookie, got {r.status_code}"


def test_report_workspace_isolation(new_user_session):
    r = new_user_session.get(f"{API}/analyses/demo-analysis-0001/report", timeout=15)
    assert r.status_code == 404


def test_report_nonexistent(demo_session):
    r = demo_session.get(f"{API}/analyses/no-such-analysis-xyz/report", timeout=15)
    assert r.status_code == 404


# OCR/upload regression: text PDF still uploads and Processes
def test_document_upload_text_pdf_processed(demo_session):
    pdf = _make_pdf_bytes()
    files = {"file": ("TEST_ocr_regress.pdf", pdf, "application/pdf")}
    data = {"doc_type": "company", "category": "Other"}
    r = demo_session.post(f"{API}/documents", files=files, data=data, timeout=90)
    assert r.status_code == 200, r.text
    doc = r.json()
    try:
        # OCR change should not break upload flow; accept Processed or Needs Review
        # for minimal text PDFs, but never Failed.
        assert doc.get("status") in ("Processed", "Needs Review"), f"status={doc.get('status')}"
        assert isinstance(doc.get("page_count"), int) and doc["page_count"] > 0
    finally:
        demo_session.delete(f"{API}/documents/{doc['id']}", timeout=15)


# Semantic retrieval regression: fresh analysis should pass turnover, fail 'similar projects'
def test_semantic_retrieval_analysis(demo_session):
    body = {
        "tender_name": "TEST_Semantic_Run",
        "tender_document_id": "demo-tender-doc-0001",
        "company_id": "demo-company-0001",
        "evidence_document_ids": [f"cd-{i}" for i in range(1, 8)],
    }
    r = demo_session.post(f"{API}/analyses", json=body, timeout=30)
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    try:
        deadline = time.time() + 180
        final = None
        while time.time() < deadline:
            s = demo_session.get(f"{API}/analyses/{aid}/status", timeout=15).json()
            if s["status"] == "completed":
                final = s
                break
            if s["status"] == "failed":
                pytest.fail(f"pipeline failed: {s.get('error')}")
            time.sleep(4)
        assert final is not None, "analysis did not complete in time"
        reqs = demo_session.get(f"{API}/analyses/{aid}/requirements", timeout=15).json()
        assert len(reqs) >= 3
        # Similar completed projects -> FAIL
        similar = [r for r in reqs if "similar" in r["name"].lower()]
        assert similar, f"no similar-projects requirement found: {[r['name'] for r in reqs]}"
        assert similar[0]["status"] == "FAIL", f"similar-projects: {similar[0]['status']}"
        # Turnover -> PASS (42 Cr >= 30 Cr via semantic match)
        turnover = [r for r in reqs if "turnover" in r["name"].lower()]
        assert turnover, f"no turnover requirement: {[r['name'] for r in reqs]}"
        assert turnover[0]["status"] == "PASS", f"turnover: {turnover[0]['status']}"
    finally:
        demo_session.delete(f"{API}/analyses/{aid}", timeout=15)
    # Demo dashboard remains total=1
    stats = demo_session.get(f"{API}/dashboard", timeout=15).json()["stats"]
    assert stats["total"] == 1


# =============================================================================
# Phase 2 — Portfolio Intelligence
# =============================================================================

# --- Capacity ---
def test_capacity_seeded(demo_session):
    r = demo_session.get(f"{API}/capacity", timeout=15)
    assert r.status_code == 200
    c = r.json()
    assert c["people"]["estimators"] == 4
    assert c["people"]["specialist_engineers"] == 1
    assert c["finance"]["working_capital_cr"] == 5
    assert len(c["equipment"]) == 3
    names = {e["name"] for e in c["equipment"]}
    assert {"Launching Girder", "Concrete Batching Plant", "Crawler Crane 80T"} <= names
    # source labels must be present
    assert isinstance(c.get("sources"), dict) and c["sources"]


def test_capacity_persist(demo_session):
    r = demo_session.get(f"{API}/capacity", timeout=15)
    c = r.json()
    original = c["people"]["estimators"]
    new_val = original + 1
    body = {
        "people": {**c["people"], "estimators": new_val},
        "finance": c["finance"],
        "equipment": c["equipment"],
        "time": c["time"],
        "sources": c.get("sources", {}),
    }
    r2 = demo_session.put(f"{API}/capacity", json=body, timeout=15)
    assert r2.status_code == 200
    assert r2.json()["people"]["estimators"] == new_val
    # verify persisted
    r3 = demo_session.get(f"{API}/capacity", timeout=15)
    assert r3.json()["people"]["estimators"] == new_val
    # revert
    body["people"]["estimators"] = original
    demo_session.put(f"{API}/capacity", json=body, timeout=15)


# --- Opportunities ---
def test_opportunities_seeded(demo_session):
    r = demo_session.get(f"{API}/opportunities", timeout=15)
    assert r.status_code == 200
    opps = r.json()
    assert len(opps) == 5
    ids = {o["id"] for o in opps}
    assert ids == {"opp-A", "opp-B", "opp-C", "opp-D", "opp-E"}


def test_opportunity_stage_patch_persists(demo_session):
    r = demo_session.get(f"{API}/opportunities", timeout=15)
    opps = r.json()
    target = next(o for o in opps if o["id"] == "opp-C")
    original = target["stage"]
    new_stage = "READY" if original != "READY" else "REVIEW"
    r2 = demo_session.patch(f"{API}/opportunities/opp-C", json={"stage": new_stage}, timeout=15)
    assert r2.status_code == 200
    assert r2.json()["stage"] == new_stage
    # verify via list
    r3 = demo_session.get(f"{API}/opportunities", timeout=15)
    updated = next(o for o in r3.json() if o["id"] == "opp-C")
    assert updated["stage"] == new_stage
    # revert
    demo_session.patch(f"{API}/opportunities/opp-C", json={"stage": original}, timeout=15)


# --- Optimize (deterministic) ---
def test_portfolio_optimize_baseline_value(demo_session):
    r = demo_session.post(f"{API}/portfolio/optimize", json={"objective": "value"}, timeout=20)
    assert r.status_code == 200
    d = r.json()
    baseline = d["baseline"]
    pursue_ids = {o["id"] for o in baseline["pursue"]}
    watch_ids = {o["id"] for o in baseline["watch"]}
    defer_ids = {o["id"] for o in baseline["defer"]}
    assert pursue_ids == {"opp-A", "opp-C"}, f"pursue: {pursue_ids}"
    assert watch_ids == {"opp-B", "opp-E"}, f"watch: {watch_ids}"
    assert defer_ids == {"opp-D"}, f"defer: {defer_ids}"
    totals = baseline["totals"]
    assert totals["specialist_engineers"]["used"] == 1
    assert totals["specialist_engineers"]["limit"] == 1
    # WATCH items must include a note explaining the conflict (specialist/equipment)
    for w in baseline["watch"]:
        assert w.get("note")
    # DEFER items include reason
    for de in baseline["defer"]:
        assert de.get("note")
    # opp-D specifically low qualification
    d_note = next(x for x in baseline["defer"] if x["id"] == "opp-D")["note"].lower()
    assert "qualification" in d_note or "58" in d_note


def test_portfolio_optimize_whatif_specialist(demo_session):
    r = demo_session.post(f"{API}/portfolio/optimize",
                          json={"objective": "value", "overrides": {"specialist_engineers": 2}},
                          timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert "scenario" in d and "diff" in d
    added_ids = {a["id"] for a in d["diff"]["added"]}
    assert "opp-B" in added_ids, f"expected opp-B added; got {d['diff']}"
    added_names = " ".join((a.get("name") or "") for a in d["diff"]["added"])
    assert "Chennai" in added_names


# --- Conflicts ---
def test_portfolio_conflicts(demo_session):
    r = demo_session.get(f"{API}/portfolio/conflicts", timeout=15)
    assert r.status_code == 200
    conflicts = r.json()["conflicts"]
    resources = [c["resource"] for c in conflicts]
    assert any("Specialist engineers" in x for x in resources), f"got: {resources}"
    # Find specialist entry: 3 opps need it, 1 available
    spec = next(c for c in conflicts if "Specialist engineers" in c["resource"])
    assert spec["available"] == 1
    assert len(spec["opportunities"]) >= 3
    assert any("Working capital" in x for x in resources), f"got: {resources}"


# --- Summary ---
def test_portfolio_summary(demo_session):
    r = demo_session.get(f"{API}/portfolio/summary", timeout=15)
    assert r.status_code == 200
    s = r.json()
    assert s["total"] == 5
    assert s["pursue"] == 2
    assert s["watch"] == 2
    assert s["defer"] == 1


# --- Compare ---
def test_portfolio_compare(demo_session):
    r = demo_session.post(f"{API}/portfolio/compare",
                          json={"opportunity_ids": ["opp-A", "opp-B", "opp-C"]}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["best_value_id"] == "opp-A"  # 412 Cr
    assert d["best_lowrisk_id"] == "opp-C"  # LOW
    assert d["best_qualification_id"] == "opp-B"  # 91
    assert isinstance(d["best_portfolio"], list)


def test_portfolio_compare_requires_two(demo_session):
    r = demo_session.post(f"{API}/portfolio/compare",
                          json={"opportunity_ids": ["opp-A"]}, timeout=15)
    assert r.status_code == 400


# --- Objectives ---
def test_portfolio_objectives(demo_session):
    r = demo_session.get(f"{API}/portfolio/objectives", timeout=15)
    assert r.status_code == 200
    objs = r.json()
    keys = {o["key"] for o in objs}
    assert {"value", "balanced", "risk", "qualification", "strategic"} <= keys
