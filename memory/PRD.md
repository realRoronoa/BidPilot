# BidPilot — PRD

## Original problem statement
Build the complete BidPilot web application: an AI-powered pre-bid intelligence platform for
construction contractors that answers "Should we bid on this tender?" It reads tender PDFs, extracts
eligibility/compliance/technical/personnel/equipment/financial requirements, matches them against
company evidence via RAG with page-level traceability, identifies risks, computes a transparent
readiness score, and produces a BID / BID WITH CONDITIONS / NO-BID recommendation with an action plan.
Serious B2B SaaS, "Site Office" design system, honest about implemented capabilities (no fake AI,
no fake payments, no fabricated evidence).

## Architecture (this env: React + FastAPI + MongoDB, adapted from the spec's Next/Postgres)
- FastAPI modular backend: core (auth/db/decision), rag (parse/chunk/retrieve), ai (Claude agents),
  services (analysis orchestration, object storage), routes (auth + workspace).
- Claude Sonnet (Anthropic) or OpenAI models directly. Local filesystem / S3 object storage for PDF binaries.
- React SPA with AuthContext, AppShell, and 12 pages. Site Office design (Spectral/Inter/IBM Plex Mono,
  paper/navy/amber, decision stamps).

## User personas
Bid managers, tender/proposal managers, BD teams, estimation & procurement teams at SME→enterprise
construction contractors.

## Core requirements (static)
Auth + demo login; workspace/company/document management; new-analysis wizard; real document
processing (parse, chunk, retrieve); structured AI analysis with anti-hallucination; requirement
matching; eligibility/compliance/technical/risk analysis; evidence traceability + viewer;
deterministic decision synthesis; readiness score; action plan; history; notifications; settings;
users & roles; sandbox billing/usage/invoices; audit trail; responsive/accessible UI; error/loading/
empty states; seeded demo.

## Implemented (2026-08-29)
- JWT cookie auth (login/signup/logout/forgot/reset/refresh) + working Demo Login + email-keyed brute-force lockout.
- Seeded demo workspace: ABC Infrastructure + Bengaluru Metro Corridor-7 (BID WITH CONDITIONS, 76%),
  requirements, risks, action items, deadlines, notifications, plans/subscription/usage/invoices, audit.
- Dashboard, Analyses list (search/filter/delete), New Analysis 5-step wizard with real upload→AI.
- Analysis Workspace tabs: Overview, Requirements, Eligibility, Compliance, Technical, Risks,
  Evidence, Decision (stamp + report), Action Plan (persisting tasks).
- Evidence Viewer (tender vs company source, page text, conclusion).
- Company management, Documents (object storage upload, expiry alerts, download, delete).
- Notifications center, Users & Roles, Sandbox Billing, Settings (5 sections).
- Real AI pipeline verified end-to-end (extraction, matching, risk, decision).
- Docs (README, ARCHITECTURE, AI_PIPELINE, RAG, BILLING, DEMO).

### Enhancements (2026-08-29, round 2) — all tested (25/25 backend, frontend export flow)
- OCR: scanned/image-only PDFs are now OCR'd (tesseract + pdf2image) so they become analyzable; still honest when OCR yields nothing.
- Server-side branded PDF report: GET /api/analyses/{id}/report (reportlab) — real downloadable file, auth-scoped, status-checked. Decision tab "Export report" downloads it.
- Semantic retrieval: local embeddings (fastembed BAAI/bge-small-en-v1.5, 384-dim) with keyword fallback; company chunks embedded once per analysis. Matches evidence even when wording differs.

## Backlog / remaining (prioritized)
- P1: password change wired to backend (Settings/Security currently demo-only for change form).
- P2: MongoDB Atlas Vector Search for large-scale retrieval (currently in-memory cosine over per-analysis chunks).
- P2: portfolio optimizer uses O(2^n) brute force up to 15 opps (greedy fallback beyond) — consider ILP/beam search for very large pipelines.
- P2: real payment provider (Stripe) behind billing; global search backend; notification preferences persistence.

### Phase 2 — Portfolio Intelligence (2026-08-29) — all tested (36/36 backend, full frontend flow)
- Capacity Manager: people/finance/equipment/time with per-field source labels (VERIFIED / USER PROVIDED / AI EXTRACTED / AI INFERRED / ASSUMPTION / NEEDS REVIEW). GET/PUT /api/capacity.
- Opportunity Pipeline: multiple opportunities with resource profiles + stages; compare 2+ side by side. /api/opportunities CRUD.
- Deterministic Portfolio Optimizer (no LLM): feasible-combination search, objective scoring (value/qualification/risk/strategic/balanced), explainable PURSUE / WATCH / DEFER, capacity-utilization meters. /api/portfolio/optimize|conflicts|compare|summary.
- Resource-conflict detection (specialist engineers, capital, estimators, equipment, deadlines).
- What-If simulator: temporary capacity overrides recompute the portfolio and show what changed (never mutates saved capacity).
- Portfolio Impact panel inside the analysis Overview; portfolio banner on the main Dashboard.
- Demo seed: capacity (4 estimators, 1 specialist, ₹5 Cr) + 5 opportunities crafted so baseline pursues A+C, and raising the specialist engineer 1→2 adds Chennai (B).

### Phase 2.1 — follow-ups (2026-08-29) — all tested (6/6 new, full regression)
- Add-to-Portfolio: one-click POST /api/analyses/{id}/to-opportunity creates an opportunity from a completed analysis with AI-inferred resource needs (labelled AI_INFERRED), qualification/risk from the decision. Idempotent (won't duplicate). Timeout-guarded with safe defaults.
- Portfolio PDF report: GET /api/portfolio/report — branded reportlab PDF with recommended portfolio, conflicts, and capacity assumptions. Download button on the Portfolio page.
- Saved What-If scenarios: named scenarios (objective + overrides) persisted per workspace; save/load/delete in the simulator. /api/portfolio/scenarios CRUD.
- Capacity-from-evidence: POST /api/capacity/suggest infers people/equipment from company documents (AI_INFERRED, does NOT persist until the user saves). Timeout-guarded.

### Phase 2.2 — follow-ups (2026-08-29) — all tested (48/48 backend sequential, both frontend flows)
- Edit Suggested Needs: inline editor in the analysis Portfolio Impact panel to tweak an opportunity's resource needs (estimators/specialists/capital/bid-security/effort/value); edited fields are relabelled USER_PROVIDED. Uses PATCH /api/opportunities/{id}.
- Scenario Compare: POST /api/portfolio/scenarios/compare {left_id,right_id,objective} (accepts 'baseline' sentinel; rejects same-vs-same) returns each recommended portfolio + only-left/in-both/only-right diff. Side-by-side panel on the Portfolio page.

## Next tasks
1. Wire Settings → Security password change to `/api/auth/reset-password`-style endpoint.
2. Add embeddings retrieval option behind the RAG abstraction.
3. Optional Stripe test-mode integration for billing.
