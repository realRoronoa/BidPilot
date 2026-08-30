from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.db import create_indexes
from core.auth import hash_password, verify_password
from core.db import db
from routes.auth_routes import router as auth_router
from routes.workspace_routes import router as workspace_router
from routes.portfolio_routes import router as portfolio_router
from seed_demo import seed_demo
from portfolio.seed_portfolio import seed_portfolio
from services.storage import init_storage

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bidpilot")

import re
from starlette.types import ASGIApp, Scope, Receive, Send

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


@app.on_event("startup")
async def startup():
    await create_indexes()
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
