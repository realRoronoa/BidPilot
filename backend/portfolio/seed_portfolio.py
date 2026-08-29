"""Seeds demo capacity + a multi-opportunity pipeline (idempotent).

Crafted so the portfolio value is obvious:
- Specialist engineer (1 available) is the binding constraint across A/B/E.
- Best portfolio by value under baseline = A + Hubballi Water (C).
- What-if: specialist 1 -> 2 makes Chennai (B) feasible => A + B + C.
- What-if: working capital +2 => a previously value-excluded opp becomes attractive.
All values are clearly fictional demo data.
"""
from datetime import datetime, timezone, timedelta
from core.db import db
from seed_demo import DEMO_WS_ID, DEMO_ANALYSIS_ID


def _iso(dt):
    return dt.isoformat()


def now():
    return datetime.now(timezone.utc)


async def seed_portfolio():
    if await db.capacity.find_one({"workspace_id": DEMO_WS_ID}):
        return

    await db.capacity.insert_one({
        "id": "demo-capacity-0001", "workspace_id": DEMO_WS_ID,
        "people": {"estimators": 4, "bid_managers": 2, "engineers": 4, "project_managers": 2, "specialist_engineers": 1},
        "finance": {"working_capital_cr": 5, "bid_security_capacity_cr": 2},
        "equipment": [
            {"name": "Launching Girder", "total": 1, "committed": 0},
            {"name": "Concrete Batching Plant", "total": 1, "committed": 0},
            {"name": "Crawler Crane 80T", "total": 1, "committed": 0},
        ],
        "time": {"bid_team_capacity_days": 40, "current_workload_days": 8},
        "sources": {
            "estimators": "USER_PROVIDED", "bid_managers": "USER_PROVIDED", "engineers": "USER_PROVIDED",
            "project_managers": "USER_PROVIDED", "specialist_engineers": "USER_PROVIDED",
            "working_capital_cr": "USER_PROVIDED", "bid_security_capacity_cr": "USER_PROVIDED",
            "Launching Girder": "VERIFIED", "Concrete Batching Plant": "VERIFIED", "Crawler Crane 80T": "VERIFIED",
            "bid_team_capacity_days": "ASSUMPTION", "current_workload_days": "USER_PROVIDED",
        },
    })

    src = {"estimators": "AI_INFERRED", "specialist_engineers": "AI_INFERRED",
           "capital_cr": "AI_INFERRED", "bid_security_cr": "AI_EXTRACTED", "bid_effort_days": "ASSUMPTION"}

    opps = [
        {"id": "opp-A", "name": "Bengaluru Metro Corridor-7 — Civil Works C4", "client": "BMRCL",
         "location": "Bengaluru, KA", "value_cr": 412, "deadline": "2025-09-10", "stage": "READY",
         "analysis_id": DEMO_ANALYSIS_ID, "qualification_fit": 76, "risk": "MEDIUM", "strategic_priority": 4,
         "resources": {"estimators": 1, "engineers": 2, "project_managers": 1, "specialist_engineers": 1,
                       "capital_cr": 1.5, "bid_security_cr": 0.85, "bid_effort_days": 12,
                       "equipment": [{"name": "Launching Girder", "qty": 1}]},
         "resource_sources": src},
        {"id": "opp-B", "name": "Chennai Elevated Corridor Package B2", "client": "CMRL",
         "location": "Chennai, TN", "value_cr": 260, "deadline": "2025-09-18", "stage": "REVIEW",
         "analysis_id": None, "qualification_fit": 91, "risk": "HIGH", "strategic_priority": 5,
         "resources": {"estimators": 1, "engineers": 2, "project_managers": 1, "specialist_engineers": 1,
                       "capital_cr": 1.2, "bid_security_cr": 0.6, "bid_effort_days": 10, "equipment": []},
         "resource_sources": src},
        {"id": "opp-C", "name": "Hubballi Water Supply Network", "client": "KUWSDB",
         "location": "Hubballi, KA", "value_cr": 90, "deadline": "2025-09-25", "stage": "ANALYZING",
         "analysis_id": None, "qualification_fit": 85, "risk": "LOW", "strategic_priority": 3,
         "resources": {"estimators": 1, "engineers": 1, "project_managers": 1, "specialist_engineers": 0,
                       "capital_cr": 1.0, "bid_security_cr": 0.3, "bid_effort_days": 6, "equipment": []},
         "resource_sources": src},
        {"id": "opp-D", "name": "Mumbai Coastal Industrial Warehouse", "client": "JNPA",
         "location": "Navi Mumbai, MH", "value_cr": 150, "deadline": "2025-09-14", "stage": "DISCOVERED",
         "analysis_id": None, "qualification_fit": 58, "risk": "HIGH", "strategic_priority": 2,
         "resources": {"estimators": 1, "engineers": 1, "project_managers": 1, "specialist_engineers": 0,
                       "capital_cr": 3.5, "bid_security_cr": 1.4, "bid_effort_days": 9,
                       "equipment": [{"name": "Crawler Crane 80T", "qty": 1}]},
         "resource_sources": src},
        {"id": "opp-E", "name": "Mysuru Ring Road Flyover", "client": "KRDCL",
         "location": "Mysuru, KA", "value_cr": 180, "deadline": "2025-09-20", "stage": "REVIEW",
         "analysis_id": None, "qualification_fit": 88, "risk": "MEDIUM", "strategic_priority": 4,
         "resources": {"estimators": 1, "engineers": 2, "project_managers": 1, "specialist_engineers": 1,
                       "capital_cr": 1.3, "bid_security_cr": 0.5, "bid_effort_days": 8, "equipment": []},
         "resource_sources": src},
    ]
    for i, o in enumerate(opps):
        o["workspace_id"] = DEMO_WS_ID
        o["portfolio_override"] = None
        o["portfolio_override_reason"] = None
        o["created_at"] = _iso(now() - timedelta(days=10 - i))
    await db.opportunities.insert_many(opps)
