# Architecture

## Backend (`/app/backend`)
- `server.py` — FastAPI app, CORS, startup (indexes, admin+demo seed, storage init), router include.
- `core/` — `db.py` (Mongo client + indexes), `auth.py` (JWT cookies, bcrypt, get_current_user), `decision.py` (deterministic decision rules).
- `rag/pipeline.py` — page-aware PDF parsing, chunking, keyword (BM25-lite) retrieval with source metadata.
- `ai/pipeline.py` — Claude agents: requirement extractor, evidence matcher, risk analyzer, action planner. Strict anti-hallucination prompts, JSON validation.
- `services/analysis_service.py` — orchestrates the 9-stage pipeline as a background task.
- `services/storage.py` — Emergent object storage for PDF binaries.
- `routes/auth_routes.py`, `routes/workspace_routes.py` — all API endpoints under `/api`.
- `seed_demo.py` — idempotent demo workspace seeding.

## Frontend (`/app/frontend/src`)
- `context/AuthContext.jsx` — cookie session, login/demo/signup/logout.
- `components/common.jsx` — StatusBadge, DecisionStamp, ReadinessRing, ScoreBar, SourceTag, EmptyState.
- `components/layout/AppShell.jsx` — blueprint-navy sidebar + topbar, mobile drawer.
- `pages/` — Login, Dashboard, Analyses, NewAnalysis (wizard), AnalysisWorkspace (9 tabs), EvidenceViewer, Company, Documents, Notifications, Users, Billing, Settings.

## Data model (MongoDB collections)
users, workspaces, workspace_members, companies, company_projects, company_personnel,
company_equipment, documents (tender + company, with page text), analyses, requirements,
risks, action_items, notifications, plans, subscriptions, usage_records, invoices, audit_events,
password_reset_tokens, login_attempts.

Workspace isolation: every domain query is filtered by `workspace_id` derived from the authenticated user.

## Auth
JWT access (7d) + refresh (30d) in httpOnly, Secure, SameSite=None cookies. Brute-force lockout on
login. Admin + demo users seeded on startup.
