# AI Pipeline

Provider abstraction: `ai/pipeline.py` uses `emergentintegrations.LlmChat` with
`anthropic / claude-sonnet-4-6`. The model can be swapped by changing `MODEL_PROVIDER` / `MODEL_NAME`.

## Stages (`services/analysis_service.py`)
1. Reading tender documents — load page-aware text.
2. Extracting requirements — Claude returns structured requirements (category, tender_requirement, source_page) + deadlines.
3–4. Matching company qualifications — for each requirement, retrieve company evidence chunks (RAG) and ask Claude to decide PASS / FAIL / NEEDS_REVIEW with confidence + source.
5–6. Compliance & technical are derived from the categorized requirements; risks analyzed from tender text.
7. Verifying evidence — source doc/page attached to each finding.
8–9. Decision synthesis (deterministic, `core/decision.py`) + action plan.

## Anti-hallucination
- System prompts forbid inventing clauses, values, certifications, projects, or page numbers.
- Missing evidence → EVIDENCE NOT FOUND / NEEDS_REVIEW.
- The model never chooses the final decision — rules do.
- JSON output is parsed and validated; invalid items are dropped, not fabricated.

## Decision rules (configurable weights)
Eligibility 40% · Compliance 25% · Technical 20% · Risk 15%.
- ≥2 critical eligibility FAILs or eligibility < 45% → NO-BID.
- Any blockers / review items / HIGH risks → BID WITH CONDITIONS.
- Otherwise → BID.
