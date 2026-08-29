"""Phase-2.2 backend tests: Edit Suggested Needs (PATCH) + Scenario Compare.
Restores demo state on teardown (opp-A, opp-C originals; scenarios cleaned).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://qualification-ai.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def demo():
    s = requests.Session()
    r = s.post(f"{API}/auth/demo-login", timeout=30)
    assert r.status_code == 200, r.text
    return s


# ---- Edit Suggested Needs (PATCH) ----
def test_patch_opp_c_resources_persists_and_marks_user_provided(demo):
    # Snapshot original
    all_opps = demo.get(f"{API}/opportunities", timeout=15).json()
    o0 = next(o for o in all_opps if o["id"] == "opp-C")
    orig_res = dict(o0["resources"])
    orig_srcs = dict(o0.get("resource_sources") or {})
    try:
        new_res = {**orig_res, "estimators": 3, "capital_cr": 2.5}
        new_srcs = {**orig_srcs, "estimators": "USER_PROVIDED", "capital_cr": "USER_PROVIDED"}
        r = demo.patch(f"{API}/opportunities/opp-C",
                       json={"resources": new_res, "resource_sources": new_srcs}, timeout=20)
        assert r.status_code == 200, r.text
        got = r.json()
        assert got["resources"]["estimators"] == 3
        assert got["resources"]["capital_cr"] == 2.5
        assert got["resource_sources"]["estimators"] == "USER_PROVIDED"
        assert got["resource_sources"]["capital_cr"] == "USER_PROVIDED"

        # Verify persistence via GET (list)
        g = next(o for o in demo.get(f"{API}/opportunities", timeout=15).json() if o["id"] == "opp-C")
        assert g["resources"]["estimators"] == 3
        assert g["resources"]["capital_cr"] == 2.5
        assert g["resource_sources"]["capital_cr"] == "USER_PROVIDED"
    finally:
        # Revert to seeded values (estimators=1, capital_cr=1.0)
        r = demo.patch(f"{API}/opportunities/opp-C",
                       json={"resources": orig_res, "resource_sources": orig_srcs}, timeout=20)
        assert r.status_code == 200
        chk = next(o for o in demo.get(f"{API}/opportunities", timeout=15).json() if o["id"] == "opp-C")
        assert chk["resources"]["estimators"] == orig_res["estimators"]
        assert chk["resources"]["capital_cr"] == orig_res["capital_cr"]


def test_patch_opportunity_not_found(demo):
    r = demo.patch(f"{API}/opportunities/does-not-exist",
                   json={"resources": {"estimators": 1}}, timeout=15)
    assert r.status_code == 404


# ---- Scenario Compare ----
def test_scenario_compare_value_objective_baseline_vs_specialist(demo):
    # Create two scenarios
    a = demo.post(f"{API}/portfolio/scenarios",
                  json={"name": "TEST_+1 specialist", "objective": "value",
                        "overrides": {"specialist_engineers": 2}}, timeout=15)
    assert a.status_code == 200, a.text
    sid_a = a.json()["id"]

    b = demo.post(f"{API}/portfolio/scenarios",
                  json={"name": "TEST_more capital", "objective": "value",
                        "overrides": {"working_capital_cr": 8}}, timeout=15)
    assert b.status_code == 200, b.text
    sid_b = b.json()["id"]

    try:
        # Compare baseline vs specialist scenario
        r = demo.post(f"{API}/portfolio/scenarios/compare",
                      json={"left_id": "baseline", "right_id": sid_a, "objective": "value"},
                      timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "left" in data and "right" in data
        assert "only_left" in data and "only_right" in data and "common" in data

        left_ids = {p["id"] for p in data["left"]["pursue"]}
        right_ids = {p["id"] for p in data["right"]["pursue"]}
        only_right_ids = {p["id"] for p in data["only_right"]}

        # Baseline value pursue = [opp-A, opp-C] (Bengaluru Metro + Hubballi Water)
        assert "opp-A" in left_ids and "opp-C" in left_ids, f"baseline pursue: {left_ids}"
        # +1 specialist scenario adds Chennai Elevated (opp-B)
        assert "opp-B" in right_ids, f"scenario pursue: {right_ids}"
        assert "opp-B" in only_right_ids, f"only_right: {only_right_ids}"

        # Also try baseline vs capital scenario (smoke)
        r2 = demo.post(f"{API}/portfolio/scenarios/compare",
                       json={"left_id": "baseline", "right_id": sid_b, "objective": "value"},
                       timeout=30)
        assert r2.status_code == 200
        d2 = r2.json()
        assert "opp-A" in {p["id"] for p in d2["left"]["pursue"]}
    finally:
        for sid in (sid_a, sid_b):
            d = demo.delete(f"{API}/portfolio/scenarios/{sid}", timeout=15)
            assert d.status_code == 200

    # Verify no leftover TEST_ scenarios
    lst = demo.get(f"{API}/portfolio/scenarios", timeout=15).json()
    assert not any(s["name"].startswith("TEST_") for s in lst), f"stale scenarios: {lst}"


def test_scenario_compare_scenario_not_found(demo):
    r = demo.post(f"{API}/portfolio/scenarios/compare",
                  json={"left_id": "baseline", "right_id": "nope-xyz", "objective": "value"},
                  timeout=15)
    assert r.status_code == 404


# ---- Light regression on core determinism ----
def test_portfolio_optimize_value_still_yields_a_and_c(demo):
    r = demo.post(f"{API}/portfolio/optimize", json={"objective": "value"}, timeout=30)
    assert r.status_code == 200
    ids = {o["id"] for o in r.json()["baseline"]["pursue"]}
    assert ids == {"opp-A", "opp-C"}, f"regression: pursue={ids}"


def test_opportunities_list_is_five(demo):
    r = demo.get(f"{API}/opportunities", timeout=15)
    assert r.status_code == 200
    assert len(r.json()) == 5
