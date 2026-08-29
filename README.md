# BidPilot — Pre-bid intelligence for contractors

"Know before you bid." BidPilot is an AI-powered pre-bid qualification and decision workspace for
construction contractors. It reads a tender PDF, extracts requirements, matches them against your
company evidence, surfaces risks with page-level traceability, computes a readiness score, and
produces a BID / BID WITH CONDITIONS / NO-BID recommendation plus an action plan.

## Stack (adapted to this environment)
- Frontend: React 19 + React Router + Tailwind (Site Office design system) — `/app/frontend`
- Backend: FastAPI (modular agents/rag/services/routes) — `/app/backend`
- Database: MongoDB (workspace-isolated collections)
- File storage: Local filesystem storage (or AWS S3); extracted page text in MongoDB
- AI: Anthropic Claude (Claude 3.5 / 3.7 Sonnet) or OpenAI (GPT-4o)

## Run
- Backend: `uvicorn server:app --host 0.0.0.0 --port 8000`
- Frontend: `npm start` (or `yarn start`)

## Environment variables (`backend/.env`)
- `MONGO_URL`, `DB_NAME` — MongoDB database connection
- `JWT_SECRET` — auth token signing key
- `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) — LLM provider key
- `CORS_ORIGINS` — allowed frontend origins (e.g. `http://localhost:3000`)
- `STORAGE_DIR` (optional) / `S3_BUCKET` (optional) — file storage configuration
- `ADMIN_EMAIL` / `ADMIN_PASSWORD`, `DEMO_EMAIL` / `DEMO_PASSWORD`

## Demo login
Click **Demo Login** on the login screen (no typing). Opens a fully seeded workspace:
ABC Infrastructure Pvt Ltd + Bengaluru Metro Corridor-7 analysis (BID WITH CONDITIONS, 76%).
Credentials also in `/app/memory/test_credentials.md`.

## Docs
`docs/ARCHITECTURE.md`, `docs/AI_PIPELINE.md`, `docs/RAG.md`, `docs/BILLING.md`, `docs/DEMO.md`

## Honesty notes
- Real uploaded documents go through the real pipeline (parse → chunk → retrieve → Claude → decision).
- Demo results are seeded data, not hard-coded into the engine.
- Billing is sandbox — no real charges. Documents are not automatically legally verified.
