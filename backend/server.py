from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import re
from datetime import datetime, timezone

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send

from core.db import create_indexes, db
from core.auth import hash_password, verify_password
from routes.auth_routes import router as auth_router
from routes.workspace_routes import router as workspace_router
from routes.portfolio_routes import router as portfolio_router
from seed_demo import seed_demo
from portfolio.seed_portfolio import seed_portfolio
from services.storage import init_storage

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bidpilot")


class NormalizePathMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] in ("http", "websocket") and "path" in scope:
            scope["path"] = re.sub(r"/{2,}", "/", scope["path"])
        await self.app(scope, receive, send)


app = FastAPI(title="BidPilot API")

# Middlewares are executed in reverse order of addition (last added runs first).
# 1. NormalizePathMiddleware runs first to clean double slashes in paths.
# 2. CORSMiddleware runs next with support for all Vercel preview/production domains.
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()],
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.onrender\.com|http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(NormalizePathMiddleware)

app.include_router(auth_router)
app.include_router(workspace_router)
app.include_router(portfolio_router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "bidpilot", "message": "BidPilot Backend API is running"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "bidpilot"}


async def seed_admin():
    email = os.environ.get("ADMIN_EMAIL", "admin@bidpilot.io")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": email})
    if not existing:
        wid = "admin-ws-0001"
        now = datetime.now(timezone.utc).isoformat()
        await db.workspaces.update_one({"id": wid}, {"$setOnInsert": {
            "id": wid, "name": "BidPilot Admin", "owner_id": "admin-user-0001",
            "timezone": "UTC", "plan": "Business", "created_at": now}}, upsert=True)
        await db.users.insert_one({
            "id": "admin-user-0001", "email": email, "password_hash": hash_password(password),
            "name": "Admin", "role": "Admin", "workspace_id": wid, "avatar_initials": "AD",
            "is_demo": False, "created_at": now})
    elif not verify_password(password, existing["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(password)}})


# ----------------------------- GLOBAL PLAN SEED -----------------------------
# Plan definitions are global (no workspace_id). Seeded idempotently on every startup.
# This is the single source of truth for all plan capabilities.
# IMPORTANT: Uses $set (not $setOnInsert) so price/currency changes deploy on next restart.
GLOBAL_PLANS = [
    # Free plan — default for all new signups. No payment required.
    {"id": "plan-free", "name": "Free", "price": 0, "currency": "INR", "period": "month",
     "analyses": 2, "storage_gb": 0.5, "users": 1,
     "features": ["2 analyses / month", "500 MB storage", "1 user", "Standard analysis"],
     "is_free": True},
    # Paid plans — priced in INR for the Indian market.
    {"id": "plan-starter", "name": "Starter", "price": 3999, "currency": "INR", "period": "month",
     "analyses": 5, "storage_gb": 5, "users": 2,
     "features": ["5 analyses / month", "5 GB storage", "2 users", "Standard analysis", "Email support"],
     "is_free": False},
    {"id": "plan-pro", "name": "Professional", "price": 14999, "currency": "INR", "period": "month",
     "analyses": 30, "storage_gb": 50, "users": 10,
     "features": ["30 analyses / month", "50 GB storage", "10 users", "Advanced analysis",
                  "Evidence retention 12 months", "Team collaboration", "Priority support"],
     "is_free": False},
    {"id": "plan-business", "name": "Business", "price": 44999, "currency": "INR", "period": "month",
     "analyses": 150, "storage_gb": 250, "users": 50,
     "features": ["150 analyses / month", "250 GB storage", "50 users", "Advanced analysis",
                  "Evidence retention 36 months", "Audit trail export", "SSO", "Dedicated support"],
     "is_free": False},
]


async def seed_plans():
    """Upsert canonical plan definitions on every startup.
    Uses $set so price/currency/feature changes deploy without manual DB intervention.
    """
    for plan in GLOBAL_PLANS:
        await db.plans.update_one({"id": plan["id"]}, {"$set": plan}, upsert=True)
    logger.info("Plans seeded/verified")


@app.on_event("startup")
async def startup():
    await create_indexes()
    await seed_plans()   # must run before seed_demo() which also references plan IDs
    await seed_admin()
    await seed_demo()
    await seed_portfolio()
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed (uploads will fail until resolved): {e}")
    try:
        import asyncio
        from rag.embeddings import get_model
        asyncio.get_event_loop().run_in_executor(None, get_model)  # warm embedding model in background
    except Exception as e:
        logger.error(f"Embedding warmup skipped: {e}")
    logger.info("BidPilot API started")
