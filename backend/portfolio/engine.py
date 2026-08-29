"""Deterministic portfolio optimization engine.

The LLM never runs these calculations. Given company capacity, a set of opportunities
(each with a resource profile), and an objective, this module:
  - detects resource conflicts,
  - enumerates feasible combinations,
  - scores them by the chosen objective,
  - returns an explainable PURSUE / WATCH / DEFER split.

All numbers come from stored data (user-provided / AI-inferred / assumptions). Nothing is
invented here; missing values are treated as 0 and surfaced as "insufficient data" upstream.
"""
from itertools import combinations

RISK_REWARD = {"LOW": 3, "MEDIUM": 2, "HIGH": 1}
DEFER_QUAL_THRESHOLD = 65
PEOPLE_KEYS = ["estimators", "engineers", "project_managers", "specialist_engineers"]

OBJECTIVES = [
    {"key": "value", "label": "Maximize opportunity value"},
    {"key": "risk", "label": "Minimize risk"},
    {"key": "qualification", "label": "Maximize qualification confidence"},
    {"key": "strategic", "label": "Maximize strategic fit"},
    {"key": "balanced", "label": "Balanced portfolio"},
]


def capacity_limits(capacity, overrides=None):
    """Flatten a capacity document (+ temporary scenario overrides) into numeric limits."""
    overrides = overrides or {}
    people = dict(capacity.get("people", {}))
    finance = dict(capacity.get("finance", {}))
    time = dict(capacity.get("time", {}))
    for k, v in overrides.items():
        if k in people:
            people[k] = v
        elif k in finance:
            finance[k] = v
        elif k in time:
            time[k] = v
    equip = {}
    for e in capacity.get("equipment", []):
        name = e.get("name") or "Unnamed"
        equip[name] = max(0, (e.get("total", 0) or 0) - (e.get("committed", 0) or 0))
    limits = {
        "estimators": people.get("estimators", 0),
        "engineers": people.get("engineers", 0),
        "project_managers": people.get("project_managers", 0),
        "specialist_engineers": people.get("specialist_engineers", 0),
        "working_capital_cr": finance.get("working_capital_cr", 0),
        "bid_security_cr": finance.get("bid_security_capacity_cr", 0),
        "bid_team_days": max(0, time.get("bid_team_capacity_days", 0) - time.get("current_workload_days", 0)),
        "equipment": equip,
    }
    return limits


def _req(opp):
    r = opp.get("resources", {})
    return {
        "estimators": r.get("estimators", 0),
        "engineers": r.get("engineers", 0),
        "project_managers": r.get("project_managers", 0),
        "specialist_engineers": r.get("specialist_engineers", 0),
        "working_capital_cr": r.get("capital_cr", 0),
        "bid_security_cr": r.get("bid_security_cr", 0),
        "bid_team_days": r.get("bid_effort_days", 0),
        "equipment": {e["name"]: e.get("qty", 0) for e in r.get("equipment", [])},
    }


def _sum_reqs(opps):
    total = {k: 0 for k in ["estimators", "engineers", "project_managers", "specialist_engineers",
                            "working_capital_cr", "bid_security_cr", "bid_team_days"]}
    equip = {}
    for o in opps:
        r = _req(o)
        for k in total:
            total[k] += r[k]
        for name, qty in r["equipment"].items():
            equip[name] = equip.get(name, 0) + qty
    total["equipment"] = equip
    return total


LIMIT_LABELS = {
    "estimators": "Estimators", "engineers": "Engineers", "project_managers": "Project managers",
    "specialist_engineers": "Specialist engineers", "working_capital_cr": "Working capital (₹Cr)",
    "bid_security_cr": "Bid-security capacity (₹Cr)", "bid_team_days": "Bid-team capacity (days)",
}


def _binding(total, limits):
    """Return list of exceeded constraints for a combination."""
    issues = []
    for k, label in LIMIT_LABELS.items():
        if total[k] > limits[k] + 1e-9:
            issues.append({"resource": label, "required": round(total[k], 2), "available": round(limits[k], 2)})
    for name, qty in total["equipment"].items():
        avail = limits["equipment"].get(name, 0)
        if qty > avail:
            issues.append({"resource": name, "required": qty, "available": avail})
    return issues


def _feasible(opps, limits):
    return len(_binding(_sum_reqs(opps), limits)) == 0


def _score(opps, objective):
    if not opps:
        return -1
    if objective == "value":
        return sum(o.get("value_cr", 0) for o in opps)
    if objective == "qualification":
        return sum(o.get("qualification_fit", 0) for o in opps)
    if objective == "strategic":
        return sum(o.get("strategic_priority", 0) for o in opps)
    if objective == "risk":
        return sum(RISK_REWARD.get(o.get("risk", "MEDIUM"), 2) for o in opps)
    # balanced
    max_val = max((o.get("value_cr", 0) for o in opps), default=1) or 1
    s = 0.0
    for o in opps:
        s += (o.get("qualification_fit", 0) / 100
              + o.get("value_cr", 0) / max_val
              + RISK_REWARD.get(o.get("risk", "MEDIUM"), 2) / 3
              + o.get("strategic_priority", 0) / 5)
    return s


def optimize(opportunities, capacity, objective="balanced", overrides=None, max_brute=15):
    limits = capacity_limits(capacity, overrides)

    eligible = [o for o in opportunities if o.get("qualification_fit", 0) >= DEFER_QUAL_THRESHOLD
                and o.get("stage") != "NO-BID"]
    low_quality = [o for o in opportunities if o not in eligible]

    ids = [o["id"] for o in eligible]
    index = {o["id"]: o for o in eligible}

    best_subset, best_score = [], -1
    n = len(eligible)
    if n <= max_brute:
        for size in range(len(eligible), 0, -1):
            for combo in combinations(eligible, size):
                if _feasible(combo, limits):
                    sc = _score(combo, objective)
                    if sc > best_score or (abs(sc - best_score) < 1e-9 and len(combo) > len(best_subset)):
                        best_subset, best_score = list(combo), sc
    else:  # greedy fallback for large pipelines
        chosen = []
        pool = sorted(eligible, key=lambda o: _score([o], objective), reverse=True)
        for o in pool:
            if _feasible(chosen + [o], limits):
                chosen.append(o)
        best_subset = chosen

    pursue_ids = {o["id"] for o in best_subset}
    watch, defer = [], []
    for o in eligible:
        if o["id"] in pursue_ids:
            continue
        feasible_alone = _feasible([o], limits)
        (watch if feasible_alone else defer).append(o)
    defer += low_quality

    return {
        "objective": objective,
        "limits": limits,
        "pursue": [_explain(o, best_subset, limits, "PURSUE") for o in best_subset],
        "watch": [_explain(o, best_subset, limits, "WATCH") for o in watch],
        "defer": [_explain(o, best_subset, limits, "DEFER") for o in defer],
        "totals": _totals(best_subset, limits),
        "feasible": len(best_subset) > 0,
        "no_feasible_reason": None if best_subset else _no_feasible_reason(eligible, limits),
    }


def _totals(subset, limits):
    t = _sum_reqs(subset)
    return {
        "estimators": {"used": t["estimators"], "limit": limits["estimators"]},
        "specialist_engineers": {"used": t["specialist_engineers"], "limit": limits["specialist_engineers"]},
        "working_capital_cr": {"used": round(t["working_capital_cr"], 2), "limit": limits["working_capital_cr"]},
        "bid_security_cr": {"used": round(t["bid_security_cr"], 2), "limit": limits["bid_security_cr"]},
        "bid_team_days": {"used": t["bid_team_days"], "limit": limits["bid_team_days"]},
        "count": len(subset),
    }


def _explain(opp, pursued, limits, bucket):
    r = _req(opp)
    reasons, constraints = [], []
    reasons.append(f"{opp.get('qualification_fit', 0)}% qualification fit")
    reasons.append(f"{opp.get('risk', 'MEDIUM').title()} risk")
    if r["working_capital_cr"]:
        constraints.append(f"₹{r['working_capital_cr']} Cr working capital")
    if r["estimators"]:
        constraints.append(f"{r['estimators']} estimator(s)")
    if r["specialist_engineers"]:
        constraints.append(f"{r['specialist_engineers']} specialist engineer(s)")

    note = None
    if bucket == "PURSUE":
        reasons.append("Fits available capacity without conflicts")
    elif bucket == "WATCH":
        # find which pursued opp it collides with (specialist / equipment)
        collide = None
        for p in pursued:
            pr = _req(p)
            if r["specialist_engineers"] and pr["specialist_engineers"] and \
               r["specialist_engineers"] + pr["specialist_engineers"] > limits["specialist_engineers"]:
                collide = p["name"]; note = "Competes for the same specialist engineer"; break
            shared_eq = set(r["equipment"]) & set(pr["equipment"])
            if shared_eq:
                collide = p["name"]; note = f"Competes for the same equipment ({', '.join(shared_eq)})"; break
        if not note:
            note = "Strong individually, but excluded to keep the portfolio within capacity"
        if collide:
            note += f" as {collide}"
    else:  # DEFER
        if opp.get("qualification_fit", 0) < DEFER_QUAL_THRESHOLD:
            note = f"Low qualification fit ({opp.get('qualification_fit', 0)}%)"
        else:
            issues = _binding(_sum_reqs([opp]), limits)
            if issues:
                i = issues[0]
                note = f"Exceeds {i['resource']} on its own (needs {i['required']}, have {i['available']})"
            else:
                note = "Deferred under current constraints"

    return {
        "id": opp["id"], "name": opp.get("name"), "client": opp.get("client"),
        "value_cr": opp.get("value_cr"), "qualification_fit": opp.get("qualification_fit"),
        "risk": opp.get("risk"), "deadline": opp.get("deadline"), "stage": opp.get("stage"),
        "analysis_id": opp.get("analysis_id"),
        "bucket": bucket, "reasons": reasons, "constraints": constraints, "note": note,
    }


def _no_feasible_reason(eligible, limits):
    if not eligible:
        return {"message": "No eligible opportunities to optimize.", "constraint": None}
    # find the most-exceeded single constraint across all-opportunity total
    total = _sum_reqs(eligible)
    issues = _binding(total, limits)
    if issues:
        i = max(issues, key=lambda x: x["required"] - x["available"])
        return {"message": "Your current constraints prevent these opportunities from being pursued together.",
                "constraint": i["resource"], "required": i["required"], "available": i["available"]}
    return {"message": "No feasible portfolio under current constraints.", "constraint": None}


def detect_conflicts(opportunities, capacity):
    """Resource collisions among all opportunities (regardless of feasibility)."""
    limits = capacity_limits(capacity)
    conflicts = []

    def contributors(key, equip=None):
        out = []
        for o in opportunities:
            r = _req(o)
            qty = r["equipment"].get(equip, 0) if equip else r[key]
            if qty > 0:
                out.append({"id": o["id"], "name": o["name"], "requires": qty})
        return out

    for key, label in LIMIT_LABELS.items():
        contrib = contributors(key)
        req = sum(c["requires"] for c in contrib)
        if len(contrib) >= 2 and req > limits[key] + 1e-9:
            conflicts.append({"resource": label, "available": round(limits[key], 2),
                              "required": round(req, 2), "opportunities": contrib,
                              "message": f"{label}: {len(contrib)} opportunities need {round(req, 2)} but only {round(limits[key], 2)} available."})
    for name, avail in limits["equipment"].items():
        contrib = contributors("equipment", equip=name)
        req = sum(c["requires"] for c in contrib)
        if len(contrib) >= 2 and req > avail:
            conflicts.append({"resource": name, "available": avail, "required": req,
                              "opportunities": contrib,
                              "message": f"{name}: {len(contrib)} opportunities need {req} but only {avail} available."})

    # deadline overlaps (within 7 days) among opportunities that also compete for the
    # scarce specialist engineer — the scheduling clashes that actually matter.
    dated = [o for o in opportunities if o.get("deadline") and _req(o)["specialist_engineers"] > 0]
    for a, b in combinations(dated, 2):
        try:
            from datetime import date
            da = date.fromisoformat(a["deadline"]); db_ = date.fromisoformat(b["deadline"])
            if abs((da - db_).days) <= 10:
                conflicts.append({"resource": "Overlapping deadlines", "available": None, "required": None,
                                  "type": "deadline",
                                  "opportunities": [{"id": a["id"], "name": a["name"], "requires": a["deadline"]},
                                                    {"id": b["id"], "name": b["name"], "requires": b["deadline"]}],
                                  "message": f"{a['name']} and {b['name']} submit within days of each other and both need the specialist engineer."})
        except Exception:
            pass
    return conflicts
