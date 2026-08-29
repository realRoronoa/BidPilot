"""Configurable, deterministic decision logic. The AI never picks the outcome directly."""

WEIGHTS = {"eligibility": 0.40, "compliance": 0.25, "technical": 0.20, "risk": 0.15}


def _pct(items):
    if not items:
        return 100
    pass_count = sum(1 for i in items if i.get("status") == "PASS")
    review_count = sum(1 for i in items if i.get("status") == "NEEDS_REVIEW")
    return round((pass_count + 0.5 * review_count) / len(items) * 100)


def risk_score(risks):
    if not risks:
        return 100
    penalty = 0
    for r in risks:
        sev = r.get("severity", "LOW")
        penalty += {"HIGH": 22, "MEDIUM": 11, "LOW": 4}.get(sev, 4)
    return max(0, 100 - penalty)


def synthesize_decision(requirements, risks):
    eligibility = [r for r in requirements if r.get("category") == "Eligibility"]
    compliance = [r for r in requirements if r.get("category") == "Compliance"]
    technical = [r for r in requirements if r.get("category") in ("Technical", "Personnel", "Equipment")]
    financial = [r for r in requirements if r.get("category") == "Financial"]

    elig_pool = eligibility + financial
    elig_score = _pct(elig_pool)
    comp_score = _pct(compliance)
    tech_score = _pct(technical)
    rsk_score = risk_score(risks)

    readiness = round(
        elig_score * WEIGHTS["eligibility"]
        + comp_score * WEIGHTS["compliance"]
        + tech_score * WEIGHTS["technical"]
        + rsk_score * WEIGHTS["risk"]
    )

    blockers = [r for r in requirements if r.get("status") == "FAIL"]
    review_items = [r for r in requirements if r.get("status") == "NEEDS_REVIEW"]
    satisfied = [r for r in requirements if r.get("status") == "PASS"]

    critical_elig_fails = [r for r in elig_pool if r.get("status") == "FAIL"]
    high_risks = [r for r in risks if r.get("severity") == "HIGH"]

    # Rules — outcome/recommendation are always set by one branch below; defaults guard against
    # any future code path that skips them.
    outcome = "BID WITH CONDITIONS"
    recommendation = ""
    if len(critical_elig_fails) >= 2 or elig_score < 45:
        outcome = "NO-BID"
        recommendation = ("Critical eligibility requirements are not met. Bidding is not "
                          "recommended unless the eligibility gaps can be resolved before submission.")
    elif blockers or review_items or high_risks:
        outcome = "BID WITH CONDITIONS"
        recommendation = ("The tender is broadly within reach, but there are unresolved blockers "
                          "or items needing review. Bid only after closing the conditions listed in the action plan.")
    else:
        outcome = "BID"
        recommendation = ("Eligibility and compliance are sufficiently satisfied and risks are "
                          "acceptable. This tender is a strong candidate to pursue.")

    return {
        "outcome": outcome,
        "readiness_score": readiness,
        "eligibility": elig_score,
        "compliance": comp_score,
        "technical": tech_score,
        "risk": rsk_score,
        "satisfied_items": len(satisfied),
        "blockers": len(blockers),
        "review_items": len(review_items),
        "recommendation": recommendation,
    }
