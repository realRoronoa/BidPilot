import uuid
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from core.db import db
from core.auth import get_current_user
from portfolio.engine import optimize, detect_conflicts, OBJECTIVES

router = APIRouter(prefix="/api", tags=["portfolio"])


def ws(user):
    return user["workspace_id"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def _capacity(workspace_id):
    cap = await db.capacity.find_one({"workspace_id": workspace_id}, {"_id": 0})
    if not cap:
        cap = {
            "id": uuid.uuid4().hex, "workspace_id": workspace_id,
            "people": {"estimators": 0, "bid_managers": 0, "engineers": 0, "project_managers": 0, "specialist_engineers": 0},
            "finance": {"working_capital_cr": 0, "bid_security_capacity_cr": 0},
            "equipment": [], "time": {"bid_team_capacity_days": 0, "current_workload_days": 0},
            "sources": {},
        }
    return cap


@router.get("/capacity")
async def get_capacity(user: dict = Depends(get_current_user)):
    return await _capacity(ws(user))


class CapacityBody(BaseModel):
    people: dict
    finance: dict
    equipment: list
    time: dict
    sources: dict | None = None


@router.put("/capacity")
async def put_capacity(body: CapacityBody, user: dict = Depends(get_current_user)):
    w = ws(user)
    doc = {"workspace_id": w, "people": body.people, "finance": body.finance,
           "equipment": body.equipment, "time": body.time, "sources": body.sources or {}}
    existing = await db.capacity.find_one({"workspace_id": w})
    if existing:
        await db.capacity.update_one({"workspace_id": w}, {"$set": doc})
    else:
        doc["id"] = uuid.uuid4().hex
        await db.capacity.insert_one(doc)
    await db.audit_events.insert_one({"id": uuid.uuid4().hex, "workspace_id": w, "actor": user["name"],
                                      "event": "capacity_updated", "detail": "Updated company capacity", "created_at": now_iso()})
    return await _capacity(w)


@router.get("/opportunities")
async def list_opportunities(user: dict = Depends(get_current_user)):
    return await db.opportunities.find({"workspace_id": ws(user)}, {"_id": 0}).sort("created_at", -1).to_list(200)


class OpportunityBody(BaseModel):
    name: str
    client: str = ""
    location: str = ""
    value_cr: float | None = None
    deadline: str | None = None
    stage: str = "DISCOVERED"
    analysis_id: str | None = None
    qualification_fit: float = 0
    risk: str = "MEDIUM"
    strategic_priority: int = 3
    resources: dict = {}
    resource_sources: dict | None = None


@router.post("/opportunities")
async def create_opportunity(body: OpportunityBody, user: dict = Depends(get_current_user)):
    doc = {"id": uuid.uuid4().hex, "workspace_id": ws(user), **body.model_dump(),
           "portfolio_override": None, "portfolio_override_reason": None, "created_at": now_iso()}
    await db.opportunities.insert_one(doc)
    doc.pop("_id", None)
    return doc


class OpportunityPatch(BaseModel):
    stage: str | None = None
    strategic_priority: int | None = None
    qualification_fit: float | None = None
    risk: str | None = None
    value_cr: float | None = None
    deadline: str | None = None
    resources: dict | None = None
    resource_sources: dict | None = None
    portfolio_override: str | None = None
    portfolio_override_reason: str | None = None


@router.patch("/opportunities/{oid}")
async def patch_opportunity(oid: str, body: OpportunityPatch, user: dict = Depends(get_current_user)):
    o = await db.opportunities.find_one({"id": oid, "workspace_id": ws(user)})
    if not o:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.opportunities.update_one({"id": oid}, {"$set": updates})
    return await db.opportunities.find_one({"id": oid}, {"_id": 0})


@router.delete("/opportunities/{oid}")
async def delete_opportunity(oid: str, user: dict = Depends(get_current_user)):
    r = await db.opportunities.delete_one({"id": oid, "workspace_id": ws(user)})
    if not r.deleted_count:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    return {"ok": True}


@router.get("/portfolio/objectives")
async def objectives(user: dict = Depends(get_current_user)):
    return OBJECTIVES


class OptimizeBody(BaseModel):
    opportunity_ids: list[str] | None = None
    objective: str = "balanced"
    overrides: dict | None = None  # scenario capacity overrides (temporary)


async def _selected_opps(workspace_id, ids):
    q = {"workspace_id": workspace_id}
    if ids:
        q["id"] = {"$in": ids}
    return await db.opportunities.find(q, {"_id": 0}).to_list(200)


@router.post("/portfolio/optimize")
async def portfolio_optimize(body: OptimizeBody, user: dict = Depends(get_current_user)):
    w = ws(user)
    cap = await _capacity(w)
    opps = await _selected_opps(w, body.opportunity_ids)
    if not opps:
        raise HTTPException(status_code=400, detail="No opportunities to optimize. Add opportunities first.")
    baseline = optimize(opps, cap, body.objective)
    result = {"baseline": baseline}
    if body.overrides:
        scenario = optimize(opps, cap, body.objective, overrides=body.overrides)
        result["scenario"] = scenario
        result["diff"] = _diff(baseline, scenario)
    return result


def _diff(baseline, scenario):
    b = {o["id"] for o in baseline["pursue"]}
    s = {o["id"] for o in scenario["pursue"]}
    name = {o["id"]: o["name"] for o in baseline["pursue"] + baseline["watch"] + baseline["defer"]
            + scenario["pursue"] + scenario["watch"] + scenario["defer"]}
    added = [{"id": i, "name": name.get(i)} for i in s - b]
    removed = [{"id": i, "name": name.get(i)} for i in b - s]
    return {"added": added, "removed": removed}


@router.get("/portfolio/conflicts")
async def portfolio_conflicts(user: dict = Depends(get_current_user)):
    w = ws(user)
    cap = await _capacity(w)
    opps = await db.opportunities.find({"workspace_id": w}, {"_id": 0}).to_list(200)
    return {"conflicts": detect_conflicts(opps, cap), "capacity": cap}


class CompareBody(BaseModel):
    opportunity_ids: list[str]


@router.post("/portfolio/compare")
async def portfolio_compare(body: CompareBody, user: dict = Depends(get_current_user)):
    w = ws(user)
    opps = await _selected_opps(w, body.opportunity_ids)
    if len(opps) < 2:
        raise HTTPException(status_code=400, detail="Select at least two opportunities to compare.")
    cap = await _capacity(w)
    best_value = max(opps, key=lambda o: o.get("value_cr", 0))
    best_lowrisk = min(opps, key=lambda o: {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(o.get("risk", "MEDIUM"), 2))
    best_qual = max(opps, key=lambda o: o.get("qualification_fit", 0))
    combo = optimize(opps, cap, "balanced")
    return {
        "opportunities": opps,
        "best_value_id": best_value["id"],
        "best_lowrisk_id": best_lowrisk["id"],
        "best_qualification_id": best_qual["id"],
        "best_portfolio": [o["id"] for o in combo["pursue"]],
        "best_portfolio_detail": combo["pursue"],
    }


@router.get("/portfolio/summary")
async def portfolio_summary(user: dict = Depends(get_current_user)):
    """Dashboard-level portfolio KPIs using the balanced objective."""
    w = ws(user)
    cap = await _capacity(w)
    opps = await db.opportunities.find({"workspace_id": w}, {"_id": 0}).to_list(200)
    if not opps:
        return {"total": 0, "pursue": 0, "watch": 0, "defer": 0, "conflicts": 0,
                "recommended": [], "capacity_configured": bool(cap.get("people", {}).get("estimators"))}
    result = optimize(opps, cap, "balanced")
    conflicts = detect_conflicts(opps, cap)
    return {
        "total": len(opps), "pursue": len(result["pursue"]), "watch": len(result["watch"]),
        "defer": len(result["defer"]), "conflicts": len(conflicts),
        "recommended": result["pursue"], "totals": result["totals"],
        "capacity_configured": bool(cap.get("people", {}).get("estimators")),
    }


# ---- Add to Portfolio (from a completed analysis) ----
@router.post("/analyses/{aid}/to-opportunity")
async def analysis_to_opportunity(aid: str, user: dict = Depends(get_current_user)):
    from ai.pipeline import infer_resource_profile
    from rag.pipeline import chunk_pages  # noqa: F401 (ensures rag importable)
    w = ws(user)
    a = await db.analyses.find_one({"id": aid, "workspace_id": w}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if a.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Analysis must be completed first.")
    existing = await db.opportunities.find_one({"analysis_id": aid, "workspace_id": w}, {"_id": 0})
    if existing:
        return {"opportunity": existing, "created": False}

    tender = await db.documents.find_one({"id": a["tender_document_id"]}, {"_id": 0})
    decision = a.get("decision") or {}
    try:
        profile = await asyncio.wait_for(
            infer_resource_profile(tender.get("pages", []) if tender else [], decision), timeout=90)
    except (asyncio.TimeoutError, Exception):
        # graceful fallback — conservative defaults, clearly assumption-labelled
        rs = decision.get("risk", 100)
        profile = {"resources": {"estimators": 1, "engineers": 2, "project_managers": 1,
                                 "specialist_engineers": 0, "capital_cr": 1.0, "bid_security_cr": 0.3,
                                 "bid_effort_days": 8, "equipment": []},
                   "value_cr": None, "risk": "LOW" if rs >= 75 else "MEDIUM" if rs >= 50 else "HIGH"}

    deadline = None
    for d in (a.get("deadlines") or []):
        if d.get("date") and "submission" in (d.get("label", "").lower()):
            deadline = d["date"]; break
    if not deadline and a.get("deadlines"):
        deadline = a["deadlines"][0].get("date")

    src = {"estimators": "AI_INFERRED", "engineers": "AI_INFERRED", "project_managers": "AI_INFERRED",
           "specialist_engineers": "AI_INFERRED", "capital_cr": "AI_INFERRED",
           "bid_security_cr": "AI_EXTRACTED", "bid_effort_days": "ASSUMPTION"}
    opp = {"id": uuid.uuid4().hex, "workspace_id": w, "name": a["tender_name"],
           "client": a.get("company_name", ""), "location": "", "value_cr": profile["value_cr"],
           "deadline": deadline, "stage": "REVIEW", "analysis_id": aid,
           "qualification_fit": decision.get("readiness_score", 0), "risk": profile["risk"],
           "strategic_priority": 3, "resources": profile["resources"], "resource_sources": src,
           "portfolio_override": None, "portfolio_override_reason": None, "created_at": now_iso()}
    await db.opportunities.insert_one(opp)
    await db.audit_events.insert_one({"id": uuid.uuid4().hex, "workspace_id": w, "actor": user["name"],
                                      "event": "opportunity_created", "detail": f"Added {a['tender_name']} to portfolio",
                                      "created_at": now_iso()})
    opp.pop("_id", None)
    return {"opportunity": opp, "created": True}


# ---- What-If scenarios (named, saved) ----
class ScenarioBody(BaseModel):
    name: str
    objective: str = "balanced"
    overrides: dict = {}


@router.get("/portfolio/scenarios")
async def list_scenarios(user: dict = Depends(get_current_user)):
    return await db.portfolio_scenarios.find({"workspace_id": ws(user)}, {"_id": 0}).sort("created_at", -1).to_list(50)


@router.post("/portfolio/scenarios")
async def save_scenario(body: ScenarioBody, user: dict = Depends(get_current_user)):
    doc = {"id": uuid.uuid4().hex, "workspace_id": ws(user), "name": body.name[:80],
           "objective": body.objective, "overrides": body.overrides, "created_at": now_iso()}
    await db.portfolio_scenarios.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.delete("/portfolio/scenarios/{sid}")
async def delete_scenario(sid: str, user: dict = Depends(get_current_user)):
    r = await db.portfolio_scenarios.delete_one({"id": sid, "workspace_id": ws(user)})
    if not r.deleted_count:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    return {"ok": True}


class ScenarioCompareBody(BaseModel):
    left_id: str
    right_id: str
    objective: str = "balanced"


@router.post("/portfolio/scenarios/compare")
async def compare_scenarios(body: ScenarioCompareBody, user: dict = Depends(get_current_user)):
    if body.left_id == body.right_id:
        raise HTTPException(status_code=400, detail="Pick two different scenarios to compare.")
    w = ws(user)
    cap = await _capacity(w)
    opps = await db.opportunities.find({"workspace_id": w}, {"_id": 0}).to_list(200)
    if not opps:
        raise HTTPException(status_code=400, detail="No opportunities to compare.")

    async def _resolve(sid):
        if sid == "baseline":
            return {"name": "Baseline (saved capacity)", "objective": body.objective, "overrides": {}}
        sc = await db.portfolio_scenarios.find_one({"id": sid, "workspace_id": w}, {"_id": 0})
        if not sc:
            raise HTTPException(status_code=404, detail="Scenario not found.")
        return sc

    left = await _resolve(body.left_id)
    right = await _resolve(body.right_id)

    def _run(sc):
        res = optimize(opps, cap, sc.get("objective", "balanced"), sc.get("overrides") or {})
        return {"name": sc["name"], "objective": sc.get("objective", "balanced"),
                "overrides": sc.get("overrides") or {},
                "pursue": [{"id": o["id"], "name": o["name"]} for o in res["pursue"]],
                "totals": res["totals"]}

    lr, rr = _run(left), _run(right)
    lset = {o["id"] for o in lr["pursue"]}
    rset = {o["id"] for o in rr["pursue"]}
    names = {o["id"]: o["name"] for o in lr["pursue"] + rr["pursue"]}
    return {
        "left": lr, "right": rr,
        "only_left": [{"id": i, "name": names[i]} for i in lset - rset],
        "only_right": [{"id": i, "name": names[i]} for i in rset - lset],
        "common": [{"id": i, "name": names[i]} for i in lset & rset],
    }


# ---- Capacity suggestions from evidence (AI-inferred, not saved) ----
@router.post("/capacity/suggest")
async def suggest_capacity(user: dict = Depends(get_current_user)):
    from ai.pipeline import infer_capacity_from_evidence
    from rag.pipeline import chunk_pages
    w = ws(user)
    docs = await db.documents.find({"workspace_id": w, "doc_type": "company"}, {"_id": 0}).to_list(50)
    chunks = []
    for d in docs:
        chunks.extend(chunk_pages(d.get("pages") or [], d["id"], "company", d["filename"]))
    if not chunks:
        raise HTTPException(status_code=400, detail="No company documents to infer capacity from.")
    try:
        suggestion = await asyncio.wait_for(infer_capacity_from_evidence(chunks), timeout=90)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Capacity inference timed out. Please try again.")
    if not suggestion:
        raise HTTPException(status_code=502, detail="Could not infer capacity from evidence.")
    return {"suggestion": suggestion, "source": "AI_INFERRED"}


# ---- Portfolio PDF report ----
@router.get("/portfolio/report")
async def portfolio_report(objective: str = "balanced", user: dict = Depends(get_current_user)):
    from services.report import build_portfolio_report
    w = ws(user)
    cap = await _capacity(w)
    opps = await db.opportunities.find({"workspace_id": w}, {"_id": 0}).to_list(200)
    if not opps:
        raise HTTPException(status_code=400, detail="No opportunities to report on.")
    rec = optimize(opps, cap, objective)
    conflicts = detect_conflicts(opps, cap)
    label = next((o["label"] for o in OBJECTIVES if o["key"] == objective), objective)
    pdf = build_portfolio_report(rec, conflicts, cap, label)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="BidPilot - Portfolio.pdf"'})
