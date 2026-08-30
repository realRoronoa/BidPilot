import itertools

def check_feasibility(combo, capacity):
    """
    Checks if a combination of opportunities is feasible given the company capacity.
    Returns (True, []) if feasible.
    Returns (False, [conflicts]) if infeasible.
    """
    req_capital = sum(op.get("req_capital", 0.0) for op in combo)
    req_estimators = sum(op.get("req_estimators", 0) for op in combo)
    req_specialists = sum(op.get("req_specialists", 0) for op in combo)
    req_pm = sum(op.get("req_project_managers", 0) for op in combo)

    conflicts = []
    if req_capital > capacity.get("working_capital", 0.0):
        conflicts.append(f"Capital Shortage: Need {req_capital}, Have {capacity.get('working_capital', 0.0)}")
    if req_estimators > capacity.get("estimators", 0):
        conflicts.append(f"Estimator Shortage: Need {req_estimators}, Have {capacity.get('estimators', 0)}")
    if req_specialists > capacity.get("specialists", 0):
        conflicts.append(f"Specialist Shortage: Need {req_specialists}, Have {capacity.get('specialists', 0)}")
    if req_pm > capacity.get("project_managers", 0):
        conflicts.append(f"PM Shortage: Need {req_pm}, Have {capacity.get('project_managers', 0)}")

    return len(conflicts) == 0, conflicts

def score_portfolio(combo):
    """Scores a portfolio based on value, qualification, and risk."""
    value = sum(op.get("estimated_value", 0.0) for op in combo)
    qual = sum(op.get("qualification_score", 0) for op in combo)
    risk = sum(op.get("risk_score", 0) for op in combo)
    # Simple scoring formula: high value is good, high qualification is good, high risk is bad.
    # Weight value scaled down assuming it's in millions, or just use a relative score.
    # We will just return the value as the primary score for now, minus risk penalties.
    return value + (qual * 1000) - (risk * 5000)

def optimize_portfolio(opportunities, capacity, overrides=None):
    """
    Evaluates all combinations of opportunities to find the optimal feasible portfolio.
    Overrides can be applied for What-If scenarios.
    """
    effective_cap = dict(capacity)
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                effective_cap[k] = v

    best_combo = []
    best_score = -float('inf')
    best_value = 0

    n = len(opportunities)
    if n == 0:
        return {"recommended": [], "score": 0, "value": 0, "conflicts": []}

    # Generate all subsets
    all_combos = []
    for r in range(1, n + 1):
        all_combos.extend(itertools.combinations(opportunities, r))

    for combo in all_combos:
        is_feasible, conflicts = check_feasibility(combo, effective_cap)
        if is_feasible:
            score = score_portfolio(combo)
            if score > best_score:
                best_score = score
                best_combo = combo
                best_value = sum(op.get("estimated_value", 0.0) for op in combo)

    # If no feasible combination is found (even individual opportunities exceed capacity)
    if not best_combo:
        return {"recommended": [], "score": 0, "value": 0, "conflicts": ["No feasible combination found with current capacity."]}

    return {
        "recommended": [op["id"] for op in best_combo],
        "score": best_score,
        "value": best_value,
        "conflicts": []
    }
