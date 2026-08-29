import os
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, Response, HTTPException
from pydantic import BaseModel, EmailStr, Field
import secrets

from core.db import db
from core.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class SignupBody(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    company_name: str | None = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class ForgotBody(BaseModel):
    email: EmailStr


class ResetBody(BaseModel):
    token: str
    password: str = Field(min_length=6)


def _public(user: dict) -> dict:
    user = dict(user)
    user.pop("password_hash", None)
    user.pop("_id", None)
    return user


@router.post("/signup")
async def signup(body: SignupBody, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    uid = uuid.uuid4().hex
    wid = uuid.uuid4().hex
    ws_name = (body.company_name or f"{body.name}'s workspace")
    await db.workspaces.insert_one({
        "id": wid, "name": ws_name, "owner_id": uid, "timezone": "UTC",
        "plan": "Starter", "created_at": now_iso()})
    user = {
        "id": uid, "email": email, "password_hash": hash_password(body.password),
        "name": body.name, "role": "Owner", "workspace_id": wid,
        "avatar_initials": "".join([p[0].upper() for p in body.name.split()[:2]]) or "U",
        "is_demo": False, "created_at": now_iso()}
    await db.users.insert_one(user)
    await db.workspace_members.insert_one({
        "id": uuid.uuid4().hex, "workspace_id": wid, "user_id": uid, "name": body.name,
        "email": email, "role": "Owner", "status": "Active", "last_activity": now_iso()})
    if body.company_name:
        await db.companies.insert_one({
            "id": uuid.uuid4().hex, "workspace_id": wid, "legal_name": body.company_name,
            "registration": "", "location": "", "years_experience": 0, "turnover": "",
            "specialization": "", "readiness": 0, "created_at": now_iso(),
            "registrations": [], "certifications": []})
    await db.audit_events.insert_one({"id": uuid.uuid4().hex, "workspace_id": wid, "actor": body.name,
                                      "event": "signup", "detail": "Account created", "created_at": now_iso()})
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    return _public(user)


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    email = body.email.lower()
    # Key by email so account lockout is reliable behind rotating-IP proxies.
    ident = email
    attempt = await db.login_attempts.find_one({"identifier": ident})
    if attempt and attempt.get("count", 0) >= MAX_ATTEMPTS:
        locked_until = datetime.fromisoformat(attempt["locked_until"])
        if locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in a few minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": ident},
            {"$inc": {"count": 1},
             "$set": {"locked_until": (datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)).isoformat()}},
            upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    await db.login_attempts.delete_one({"identifier": ident})
    await db.audit_events.insert_one({"id": uuid.uuid4().hex, "workspace_id": user["workspace_id"],
                                      "actor": user["name"], "event": "login", "detail": "Signed in",
                                      "created_at": now_iso()})
    set_auth_cookies(response, create_access_token(user["id"], email), create_refresh_token(user["id"]))
    return _public(user)


@router.post("/demo-login")
async def demo_login(response: Response):
    email = os.environ.get("DEMO_EMAIL", "demo@bidpilot.io")
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=500, detail="Demo workspace is not seeded yet. Try again shortly.")
    set_auth_cookies(response, create_access_token(user["id"], email), create_refresh_token(user["id"]))
    return _public(user)


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(request: Request):
    return await get_current_user(request)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    import jwt
    from core.auth import get_jwt_secret, JWT_ALGORITHM
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        set_auth_cookies(response, create_access_token(user["id"], user["email"]),
                         create_refresh_token(user["id"]))
        return {"ok": True}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/forgot-password")
async def forgot_password(body: ForgotBody):
    user = await db.users.find_one({"email": body.email.lower()})
    # always return ok to avoid user enumeration
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "id": uuid.uuid4().hex, "token": token, "user_id": user["id"], "used": False,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)})
        print(f"[BidPilot] Password reset link: /reset-password?token={token}")
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetBody):
    rec = await db.password_reset_tokens.find_one({"token": body.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    await db.users.update_one({"id": rec["user_id"]},
                              {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True}})
    return {"ok": True}
