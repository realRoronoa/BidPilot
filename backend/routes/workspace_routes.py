import os
import uuid
import hmac
import hashlib
import tempfile
from datetime import datetime, timezone, timedelta

import razorpay

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel

from core.db import db
from core.auth import get_current_user
from rag.pipeline import parse_pdf, chunk_pages
from rag.embeddings import attach_embeddings
from services.analysis_service import run_analysis, STAGES
from services.storage import put_object, get_object, APP_NAME
from ai.portfolio import optimize_portfolio

router = APIRouter(prefix="/api", tags=["workspace"])

MAX_FILE_BYTES = 40 * 1024 * 1024  # 40 MB


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ws(user):
    return user["workspace_id"]


async def audit(workspace_id, actor, event, detail):
    await db.audit_events.insert_one({"id": uuid.uuid4().hex, "workspace_id": workspace_id,
                                      "actor": actor, "event": event, "detail": detail,
                                      "created_at": now_iso()})


# ----------------------------- DASHBOARD -----------------------------
@router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    w = ws(user)
    analyses = await db.analyses.find({"workspace_id": w}, {"_id": 0}).sort("created_at", -1).to_list(200)
    def outcome(a):
        return (a.get("decision") or {}).get("outcome")
    total = len(analyses)
    active = sum(1 for a in analyses if a["status"] in ("queued", "running"))
    bids = sum(1 for a in analyses if outcome(a) == "BID")
    conditional = sum(1 for a in analyses if outcome(a) == "BID WITH CONDITIONS")
    nobids = sum(1 for a in analyses if outcome(a) == "NO-BID")
    open_actions = await db.action_items.count_documents(
        {"analysis_id": {"$in": [a["id"] for a in analyses]}, "status": "OPEN"})
    docs_attention = await db.documents.count_documents(
        {"workspace_id": w, "verification_state": {"$in": ["Needs Review"]}})
    deadlines = []
    for a in analyses:
        for d in (a.get("deadlines") or []):
            if d.get("date"):
                deadlines.append({**d, "tender": a["tender_name"], "analysis_id": a["id"]})
    deadlines = sorted(deadlines, key=lambda x: x["date"])[:6]
    recent = [{
        "id": a["id"], "tender_name": a["tender_name"], "company_name": a.get("company_name"),
        "date": a.get("created_at"), "status": a["status"],
        "readiness": (a.get("decision") or {}).get("readiness_score"),
        "decision": outcome(a),
        "issues": ((a.get("decision") or {}).get("blockers", 0) + (a.get("decision") or {}).get("review_items", 0)),
    } for a in analyses[:8]]
    activity = await db.audit_events.find({"workspace_id": w}, {"_id": 0}).sort("created_at", -1).to_list(6)
    return {
        "stats": {"total": total, "active": active, "bids": bids, "conditional": conditional,
                  "nobids": nobids, "open_actions": open_actions, "upcoming_deadlines": len(deadlines),
                  "docs_attention": docs_attention},
        "recent_analyses": recent, "deadlines": deadlines, "activity": activity,
    }


# ----------------------------- ANALYSES -----------------------------
class CreateAnalysis(BaseModel):
    tender_name: str
    tender_document_id: str
    company_id: str
    evidence_document_ids: list[str] = []


@router.get("/analyses")
async def list_analyses(user: dict = Depends(get_current_user)):
    analyses = await db.analyses.find({"workspace_id": ws(user)}, {"_id": 0}).sort("created_at", -1).to_list(300)
    out = []
    for a in analyses:
        d = a.get("decision") or {}
        out.append({"id": a["id"], "tender_name": a["tender_name"], "company_name": a.get("company_name"),
                    "date": a.get("created_at"), "status": a["status"],
                    "readiness": d.get("readiness_score"), "decision": d.get("outcome"),
                    "issues": d.get("blockers", 0) + d.get("review_items", 0)})
    return out


@router.post("/analyses")
async def create_analysis(body: CreateAnalysis, background: BackgroundTasks,
                          user: dict = Depends(get_current_user)):
    w = ws(user)
    tender = await db.documents.find_one({"id": body.tender_document_id, "workspace_id": w}, {"_id": 0})
    if not tender:
        raise HTTPException(status_code=404, detail="Tender document not found.")
    company = await db.companies.find_one({"id": body.company_id, "workspace_id": w}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    # ---- Entitlement enforcement: check analyses_used vs analyses_limit ----
    usage_rec = await db.usage_records.find_one({"workspace_id": w}, {"_id": 0})
    if usage_rec:
        used = usage_rec.get("analyses_used", 0)
        limit = usage_rec.get("analyses_limit", 5)  # default to Starter limit if missing
        if used >= limit:
            sub = await db.subscriptions.find_one({"workspace_id": w}, {"_id": 0})
            plan_name = (sub or {}).get("plan_name", "current plan")
            raise HTTPException(
                status_code=402,
                detail=f"Analysis limit reached ({used}/{limit} used on {plan_name}). "
                       f"Please upgrade your plan to run more analyses."
            )
    # Increment analyses_used counter
    await db.usage_records.update_one(
        {"workspace_id": w},
        {"$inc": {"analyses_used": 1}},
    )

    aid = uuid.uuid4().hex
    await db.analyses.insert_one({
        "id": aid, "workspace_id": w, "company_id": body.company_id,
        "company_name": company["legal_name"], "tender_name": body.tender_name,
        "tender_document_id": body.tender_document_id, "evidence_document_ids": body.evidence_document_ids,
        "status": "queued", "stage_index": 0, "stage_label": "Queued", "decision": None,
        "deadlines": [], "created_at": now_iso(), "updated_at": now_iso(), "completed_at": None,
        "error": None, "is_demo": False})
    await audit(w, user["name"], "analysis_created", f"Created analysis: {body.tender_name}")
    background.add_task(run_analysis, aid)
    return {"id": aid, "status": "queued"}


@router.get("/analyses/{aid}")
async def get_analysis(aid: str, user: dict = Depends(get_current_user)):
    a = await db.analyses.find_one({"id": aid, "workspace_id": ws(user)}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return a


@router.get("/analyses/{aid}/status")
async def analysis_status(aid: str, user: dict = Depends(get_current_user)):
    a = await db.analyses.find_one({"id": aid, "workspace_id": ws(user)},
                                   {"_id": 0, "status": 1, "stage_index": 1, "stage_label": 1, "error": 1})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return {**a, "stages": STAGES}


@router.post("/analyses/{aid}/run")
async def rerun_analysis(aid: str, background: BackgroundTasks, user: dict = Depends(get_current_user)):
    a = await db.analyses.find_one({"id": aid, "workspace_id": ws(user)}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    await db.analyses.update_one({"id": aid}, {"$set": {"status": "queued", "stage_index": 0,
                                                        "error": None, "updated_at": now_iso()}})
    background.add_task(run_analysis, aid)
    return {"id": aid, "status": "queued"}


@router.delete("/analyses/{aid}")
async def delete_analysis(aid: str, user: dict = Depends(get_current_user)):
    a = await db.analyses.find_one({"id": aid, "workspace_id": ws(user)})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    await db.analyses.delete_one({"id": aid})
    await db.requirements.delete_many({"analysis_id": aid})
    await db.risks.delete_many({"analysis_id": aid})
    await db.action_items.delete_many({"analysis_id": aid})
    return {"ok": True}


async def _reqs(aid, w):
    a = await db.analyses.find_one({"id": aid, "workspace_id": w}, {"_id": 0, "id": 1})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return await db.requirements.find({"analysis_id": aid}, {"_id": 0}).to_list(200)


@router.get("/analyses/{aid}/requirements")
async def get_requirements(aid: str, user: dict = Depends(get_current_user)):
    return await _reqs(aid, ws(user))


@router.get("/analyses/{aid}/eligibility")
async def get_eligibility(aid: str, user: dict = Depends(get_current_user)):
    reqs = await _reqs(aid, ws(user))
    return [r for r in reqs if r["category"] in ("Eligibility", "Financial")]


@router.get("/analyses/{aid}/compliance")
async def get_compliance(aid: str, user: dict = Depends(get_current_user)):
    reqs = await _reqs(aid, ws(user))
    items = [r for r in reqs if r["category"] == "Compliance"]
    groups = {"Available": [], "Missing": [], "Needs Review": []}
    for r in items:
        if r["status"] == "PASS":
            groups["Available"].append(r)
        elif r["status"] == "FAIL":
            groups["Missing"].append(r)
        else:
            groups["Needs Review"].append(r)
    return {"items": items, "groups": groups}


@router.get("/analyses/{aid}/technical")
async def get_technical(aid: str, user: dict = Depends(get_current_user)):
    reqs = await _reqs(aid, ws(user))
    return [r for r in reqs if r["category"] in ("Technical", "Personnel", "Equipment")]


@router.get("/analyses/{aid}/risks")
async def get_risks(aid: str, user: dict = Depends(get_current_user)):
    a = await db.analyses.find_one({"id": aid, "workspace_id": ws(user)}, {"_id": 0, "id": 1})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return await db.risks.find({"analysis_id": aid}, {"_id": 0}).to_list(100)


@router.get("/analyses/{aid}/evidence")
async def get_evidence(aid: str, user: dict = Depends(get_current_user)):
    return await _reqs(aid, ws(user))


@router.get("/analyses/{aid}/evidence/{eid}")
async def get_evidence_item(aid: str, eid: str, user: dict = Depends(get_current_user)):
    w = ws(user)
    a = await db.analyses.find_one({"id": aid, "workspace_id": w}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    req = await db.requirements.find_one({"id": eid, "analysis_id": aid}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Evidence item not found.")
    tender_doc = await db.documents.find_one({"id": a["tender_document_id"]}, {"_id": 0})
    tender_page_text = None
    if tender_doc and req.get("source_page"):
        for p in tender_doc.get("pages", []):
            if p["page_number"] == req["source_page"]:
                tender_page_text = p["text"]
                break
    company_doc = None
    company_page_text = None
    if req.get("evidence_source_document"):
        company_doc = await db.documents.find_one(
            {"workspace_id": w, "filename": req["evidence_source_document"]}, {"_id": 0})
        if company_doc and req.get("evidence_source_page"):
            for p in company_doc.get("pages", []):
                if p["page_number"] == req["evidence_source_page"]:
                    company_page_text = p["text"]
                    break
    return {
        "requirement": req,
        "tender": {"filename": tender_doc["filename"] if tender_doc else None,
                   "page": req.get("source_page"), "page_text": tender_page_text,
                   "page_count": tender_doc.get("page_count") if tender_doc else None},
        "company": {"filename": req.get("evidence_source_document"),
                    "page": req.get("evidence_source_page"), "page_text": company_page_text},
    }


@router.get("/analyses/{aid}/decision")
async def get_decision(aid: str, user: dict = Depends(get_current_user)):
    a = await db.analyses.find_one({"id": aid, "workspace_id": ws(user)}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return {"decision": a.get("decision"), "deadlines": a.get("deadlines", []),
            "tender_name": a["tender_name"], "company_name": a.get("company_name"),
            "date": a.get("created_at")}


@router.get("/analyses/{aid}/report")
async def analysis_report(aid: str, user: dict = Depends(get_current_user)):
    a = await db.analyses.find_one({"id": aid, "workspace_id": ws(user)}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if a.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Report is only available for completed analyses.")
    from services.report import build_report
    reqs = await db.requirements.find({"analysis_id": aid}, {"_id": 0}).to_list(200)
    risks = await db.risks.find({"analysis_id": aid}, {"_id": 0}).to_list(100)
    actions = await db.action_items.find({"analysis_id": aid}, {"_id": 0}).to_list(100)
    pdf = build_report(a, a.get("decision") or {}, reqs, risks, actions)
    safe = "".join(c for c in a["tender_name"] if c.isalnum() or c in " -_")[:60].strip() or "BidPilot"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="BidPilot - {safe}.pdf"'})


@router.get("/analyses/{aid}/action-items")
async def get_actions(aid: str, user: dict = Depends(get_current_user)):
    a = await db.analyses.find_one({"id": aid, "workspace_id": ws(user)}, {"_id": 0, "id": 1})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return await db.action_items.find({"analysis_id": aid}, {"_id": 0}).to_list(100)


class ActionPatch(BaseModel):
    status: str


@router.patch("/action-items/{item_id}")
async def patch_action(item_id: str, body: ActionPatch, user: dict = Depends(get_current_user)):
    if body.status not in ("OPEN", "DONE"):
        raise HTTPException(status_code=400, detail="Invalid status.")
    item = await db.action_items.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found.")
    a = await db.analyses.find_one({"id": item["analysis_id"], "workspace_id": ws(user)})
    if not a:
        raise HTTPException(status_code=403, detail="Forbidden.")
    await db.action_items.update_one({"id": item_id}, {"$set": {"status": body.status}})
    return {"ok": True, "status": body.status}


# ----------------------------- COMPANIES -----------------------------
class CompanyBody(BaseModel):
    legal_name: str
    registration: str = ""
    location: str = ""
    years_experience: int = 0
    turnover: str = ""
    specialization: str = ""
    working_capital: float = 0.0
    estimators: int = 0
    specialists: int = 0
    project_managers: int = 0


@router.get("/companies")
async def list_companies(user: dict = Depends(get_current_user)):
    return await db.companies.find({"workspace_id": ws(user)}, {"_id": 0}).to_list(100)


@router.get("/company")
async def get_primary_company(user: dict = Depends(get_current_user)):
    c = await db.companies.find_one({"workspace_id": ws(user)}, {"_id": 0})
    if not c:
        return None
    c["projects"] = await db.company_projects.find({"company_id": c["id"]}, {"_id": 0}).to_list(100)
    c["personnel"] = await db.company_personnel.find({"company_id": c["id"]}, {"_id": 0}).to_list(100)
    c["equipment"] = await db.company_equipment.find({"company_id": c["id"]}, {"_id": 0}).to_list(100)
    return c


@router.get("/companies/{cid}")
async def get_company(cid: str, user: dict = Depends(get_current_user)):
    c = await db.companies.find_one({"id": cid, "workspace_id": ws(user)}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Company not found.")
    c["projects"] = await db.company_projects.find({"company_id": cid}, {"_id": 0}).to_list(100)
    c["personnel"] = await db.company_personnel.find({"company_id": cid}, {"_id": 0}).to_list(100)
    c["equipment"] = await db.company_equipment.find({"company_id": cid}, {"_id": 0}).to_list(100)
    return c


@router.post("/company")
async def create_company(body: CompanyBody, user: dict = Depends(get_current_user)):
    cid = uuid.uuid4().hex
    doc = {"id": cid, "workspace_id": ws(user), **body.model_dump(), "readiness": 0,
           "registrations": [], "certifications": [], "created_at": now_iso()}
    await db.companies.insert_one(doc)
    await audit(ws(user), user["name"], "company_created", f"Created company {body.legal_name}")
    doc.pop("_id", None)
    return doc


@router.patch("/company/{cid}")
async def update_company(cid: str, body: CompanyBody, user: dict = Depends(get_current_user)):
    c = await db.companies.find_one({"id": cid, "workspace_id": ws(user)})
    if not c:
        raise HTTPException(status_code=404, detail="Company not found.")
    await db.companies.update_one({"id": cid}, {"$set": body.model_dump()})
    await audit(ws(user), user["name"], "company_updated", f"Updated company {body.legal_name}")
    return await db.companies.find_one({"id": cid}, {"_id": 0})


# ----------------------------- DOCUMENTS -----------------------------
@router.get("/documents")
async def list_documents(doc_type: str | None = None, user: dict = Depends(get_current_user)):
    q = {"workspace_id": ws(user)}
    if doc_type:
        q["doc_type"] = doc_type
    docs = await db.documents.find(q, {"_id": 0, "pages": 0}).sort("created_at", -1).to_list(300)
    return docs


@router.post("/documents")
async def upload_document(background: BackgroundTasks, file: UploadFile = File(...),
                          doc_type: str = Form("company"), category: str = Form("Other"),
                          company_id: str = Form(None), user: dict = Depends(get_current_user)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 40 MB).")
    did = uuid.uuid4().hex
    w = ws(user)
    storage_path = f"{APP_NAME}/uploads/{w}/{did}.pdf"
    try:
        result = put_object(storage_path, data, "application/pdf")
        storage_path = result.get("path", storage_path)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"File storage failed: {e}")
    # parse from a temp file (pypdf needs a path/stream)
    pages, is_scanned, page_count = [], False, 0
    parse_error = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            pages, is_scanned, page_count = parse_pdf(tmp.name)
    except Exception as e:
        parse_error = str(e)
    status = "Processed"
    if parse_error:
        status = "Failed"
    elif is_scanned:
        status = "Needs Review"
    doc = {
        "id": did, "workspace_id": w, "company_id": company_id, "doc_type": doc_type,
        "filename": file.filename, "category": category, "size": len(data), "page_count": page_count,
        "status": status, "verification_state": ("Needs Review" if is_scanned else "Processed"),
        "expiry": None, "storage_path": storage_path, "pages": pages,
        "is_scanned": is_scanned, "parse_error": parse_error, "is_deleted": False,
        "created_at": now_iso()}
    await db.documents.insert_one(doc)
    await audit(w, user["name"], "document_uploaded", f"Uploaded {file.filename}")
    doc.pop("_id", None)
    
    # RAG pipeline: chunk pages and compute embeddings
    # Do not save full 'pages' in the document dict sent to client
    extracted_pages = doc.pop("pages", [])
    if extracted_pages:
        chunks = chunk_pages(extracted_pages, did, doc_type, file.filename)
        # Compute embeddings in background or directly (blocking for now as requested)
        chunks = attach_embeddings(chunks)
        # Add chunks to MongoDB
        if chunks:
            # We add a UUID to each chunk to identify them
            for c in chunks:
                c["id"] = uuid.uuid4().hex
            await db.document_chunks.insert_many(chunks)

    if is_scanned:
        doc["notice"] = ("This PDF appears to be scanned; no text could be reliably extracted. "
                         "Analysis on this document may be limited (OCR not available).")
    return doc


@router.delete("/documents/{did}")
async def delete_document(did: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": did, "workspace_id": ws(user)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    await db.documents.delete_one({"id": did})
    return {"ok": True}


@router.get("/documents/{did}/download")
async def download_document(did: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": did, "workspace_id": ws(user)}, {"_id": 0})
    if not doc or not doc.get("storage_path"):
        raise HTTPException(status_code=404, detail="File not available for download (demo document).")
    try:
        content, ctype = get_object(doc["storage_path"])
    except Exception:
        raise HTTPException(status_code=404, detail="File not available for download (demo document).")
    return Response(content=content, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{doc["filename"]}"'})


# ----------------------------- NOTIFICATIONS -----------------------------
@router.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    return await db.notifications.find({"workspace_id": ws(user)}, {"_id": 0}).sort("created_at", -1).to_list(100)


@router.patch("/notifications/{nid}")
async def mark_notification(nid: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": nid, "workspace_id": ws(user)}, {"$set": {"read": True}})
    return {"ok": True}


@router.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"workspace_id": ws(user)}, {"$set": {"read": True}})
    return {"ok": True}


# ----------------------------- USERS -----------------------------
class InviteBody(BaseModel):
    name: str
    email: str
    role: str = "Member"


@router.get("/workspace/users")
async def list_users(user: dict = Depends(get_current_user)):
    return await db.workspace_members.find({"workspace_id": ws(user)}, {"_id": 0}).to_list(100)


@router.post("/workspace/users/invite")
async def invite_user(body: InviteBody, user: dict = Depends(get_current_user)):
    member = {"id": uuid.uuid4().hex, "workspace_id": ws(user), "user_id": None, "name": body.name,
              "email": body.email.lower(), "role": body.role, "status": "Invited", "last_activity": None}
    await db.workspace_members.insert_one(member)
    await audit(ws(user), user["name"], "user_invited", f"Invited {body.email}")
    member.pop("_id", None)
    return member


class MemberPatch(BaseModel):
    role: str | None = None
    status: str | None = None


@router.patch("/workspace/users/{mid}")
async def patch_member(mid: str, body: MemberPatch, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.workspace_members.update_one({"id": mid, "workspace_id": ws(user)}, {"$set": updates})
    return {"ok": True}


# ----------------------------- BILLING -----------------------------
class UpgradeBody(BaseModel):
    plan_id: str


class RzpOrderBody(BaseModel):
    plan_id: str


class RzpVerifyBody(BaseModel):
    plan_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _razorpay_client():
    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=503,
                            detail="Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
    return razorpay.Client(auth=(key_id, key_secret)), key_id, key_secret


async def _apply_plan(workspace_id: str, plan: dict, actor: str,
                      razorpay_order_id: str | None = None,
                      razorpay_payment_id: str | None = None):
    """Upsert subscription and usage records after a verified payment.

    Always upserts — works for both new and existing workspaces.
    Does NOT reset analyses_used so mid-cycle upgrades keep the usage count.
    """
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)

    sub_fields = {
        "workspace_id": workspace_id,
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "plan_price": plan["price"],
        "status": "active",
        "billing_cycle": "monthly",
        "billing_period_start": now.isoformat(),
        "billing_period_end": period_end.isoformat(),
        "next_billing_date": period_end.isoformat(),
        "activated_at": now.isoformat(),
        "sandbox": False,
        # Razorpay test mode — no real card info available
        "payment_method": None,
    }
    if razorpay_order_id:
        sub_fields["razorpay_order_id"] = razorpay_order_id
    if razorpay_payment_id:
        sub_fields["razorpay_payment_id"] = razorpay_payment_id

    await db.subscriptions.update_one(
        {"workspace_id": workspace_id},
        {"$set": sub_fields},
        upsert=True,
    )
    # Update limits only — preserve existing analyses_used count
    await db.usage_records.update_one(
        {"workspace_id": workspace_id},
        {"$set": {
            "analyses_limit": plan["analyses"],
            "storage_limit_gb": plan["storage_gb"],
            "users_limit": plan["users"],
        }},
        upsert=True,
    )
    await audit(workspace_id, actor, "subscription_changed",
                f"Upgraded to {plan['name']} via Razorpay (test)")


@router.get("/billing/plans")
async def billing_plans(user: dict = Depends(get_current_user)):
    return await db.plans.find({}, {"_id": 0}).to_list(20)


@router.get("/billing")
async def billing(user: dict = Depends(get_current_user)):
    w = ws(user)
    sub = await db.subscriptions.find_one({"workspace_id": w}, {"_id": 0})
    usage_doc = await db.usage_records.find_one({"workspace_id": w}, {"_id": 0})
    plans = await db.plans.find({}, {"_id": 0}).to_list(20)
    invoices = await db.invoices.find({"workspace_id": w}, {"_id": 0}).sort("date", -1).to_list(50)
    # Count actual active workspace members for users_used metric
    usage = None
    if usage_doc:
        active_members = await db.workspace_members.count_documents(
            {"workspace_id": w, "status": "Active"})
        usage = dict(usage_doc)
        usage["users_used"] = active_members
    return {"subscription": sub, "usage": usage, "plans": plans, "invoices": invoices, "sandbox": True}


@router.get("/billing/usage")
async def billing_usage(user: dict = Depends(get_current_user)):
    return await db.usage_records.find_one({"workspace_id": ws(user)}, {"_id": 0})


@router.get("/billing/invoices")
async def billing_invoices(user: dict = Depends(get_current_user)):
    return await db.invoices.find({"workspace_id": ws(user)}, {"_id": 0}).sort("date", -1).to_list(50)


@router.post("/billing/upgrade")
async def billing_upgrade(body: UpgradeBody, user: dict = Depends(get_current_user)):
    """Sandbox plan switch — no payment required. For testing only."""
    plan = await db.plans.find_one({"id": body.plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    w = ws(user)
    await db.subscriptions.update_one(
        {"workspace_id": w},
        {"$set": {"plan_id": plan["id"], "plan_name": plan["name"],
                  "status": "active", "sandbox": True}},
        upsert=True)
    await db.usage_records.update_one(
        {"workspace_id": w},
        {"$set": {"analyses_limit": plan["analyses"], "storage_limit_gb": plan["storage_gb"],
                  "users_limit": plan["users"]}},
        upsert=True)
    await audit(w, user["name"], "subscription_changed", f"Switched to {plan['name']} (sandbox)")
    return {"ok": True, "sandbox": True,
            "message": f"Plan switched to {plan['name']}. This is a sandbox change — no real charge was made."}


@router.post("/billing/razorpay/order")
async def razorpay_create_order(body: RzpOrderBody, user: dict = Depends(get_current_user)):
    plan = await db.plans.find_one({"id": body.plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    # Free plan has no payment — reject Razorpay order creation
    if plan.get("is_free") or plan["price"] == 0:
        raise HTTPException(status_code=400, detail="The Free plan does not require payment.")
    client, key_id, _ = _razorpay_client()
    # Amount determined server-side from plan definition — never trust client-supplied amount.
    # plan["price"] is in INR (whole rupees); Razorpay expects paise (1 INR = 100 paise).
    amount_paise = int(round(float(plan["price"]) * 100))
    try:
        order = client.order.create({
            "amount": amount_paise, "currency": "INR",
            "receipt": f"bp-{uuid.uuid4().hex[:12]}",
            "notes": {"workspace_id": ws(user), "plan_id": plan["id"], "plan_name": plan["name"]},
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not create payment order: {e}")
    return {
        "order_id": order["id"], "amount": amount_paise, "currency": "INR",
        "key_id": key_id, "plan_id": plan["id"], "plan_name": plan["name"],
        "customer_name": user.get("name"), "customer_email": user.get("email"),
    }


@router.post("/billing/razorpay/verify")
async def razorpay_verify(body: RzpVerifyBody, user: dict = Depends(get_current_user)):
    # 1. Fetch plan server-side — never trust client-supplied amount or plan name
    plan = await db.plans.find_one({"id": body.plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    # 2. Verify Razorpay HMAC signature — key_secret never leaves the server
    _, _, key_secret = _razorpay_client()
    expected = hmac.new(
        key_secret.encode(),
        f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        print(f"[Razorpay] signature verification FAILED for order {body.razorpay_order_id}")
        raise HTTPException(status_code=400,
                            detail="Payment verification failed. Your plan was not changed.")

    # 3. Idempotency — if this payment_id was already processed, return success without duplicating
    existing_record = await db.payment_records.find_one(
        {"razorpay_payment_id": body.razorpay_payment_id}, {"_id": 0})
    if existing_record:
        sub = await db.subscriptions.find_one({"workspace_id": ws(user)}, {"_id": 0}) or {}
        return {
            "ok": True, "verified": True, "idempotent": True,
            "plan_name": plan["name"],
            "plan_features": plan.get("features", []),
            "billing_period_end": sub.get("billing_period_end"),
            "message": f"Payment already verified. You are on the {plan['name']} plan.",
        }

    # 4. Create persistent payment record (unique index on razorpay_payment_id prevents duplicates)
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)
    period_label = now.strftime("%b %Y")
    invoice_number = f"BP-{now.year}-{uuid.uuid4().hex[:6].upper()}"

    try:
        await db.payment_records.insert_one({
            "id": uuid.uuid4().hex,
            "workspace_id": ws(user),
            "user_id": user["id"],
            "plan_id": plan["id"],
            "plan_name": plan["name"],
            "amount_paise": int(round(float(plan["price"]) * 100)),
            "amount_display": plan["price"],
            "currency": "INR",
            "razorpay_order_id": body.razorpay_order_id,
            "razorpay_payment_id": body.razorpay_payment_id,
            "status": "paid",
            "mode": "test",
            "billing_period_start": now.isoformat(),
            "billing_period_end": period_end.isoformat(),
            "created_at": now.isoformat(),
        })
    except Exception:
        # Duplicate key — another concurrent request already recorded this payment
        pass

    # 5. Upsert invoice record (shown in the Billing History table)
    await db.invoices.update_one(
        {"razorpay_payment_id": body.razorpay_payment_id},
        {"$setOnInsert": {
            "id": uuid.uuid4().hex,
            "workspace_id": ws(user),
            "number": invoice_number,
            "amount": plan["price"],
            "currency": "INR",
            "status": "Paid",
            "date": now.isoformat(),
            "period": period_label,
            "razorpay_payment_id": body.razorpay_payment_id,
            "razorpay_order_id": body.razorpay_order_id,
        }},
        upsert=True,
    )

    # 6. Activate subscription and update entitlements (upserts both subscription + usage)
    await _apply_plan(
        ws(user), plan, user["name"],
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
    )

    return {
        "ok": True,
        "verified": True,
        "plan_name": plan["name"],
        "plan_features": plan.get("features", []),
        "billing_period_end": period_end.isoformat(),
        "message": f"Payment verified. You are now on the {plan['name']} plan.",
    }


# ----------------------------- SETTINGS -----------------------------
@router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    workspace = await db.workspaces.find_one({"id": ws(user)}, {"_id": 0})
    return {"profile": {"name": user["name"], "email": user["email"], "role": user["role"],
                        "avatar_initials": user.get("avatar_initials")},
            "workspace": workspace}


class ProfilePatch(BaseModel):
    name: str | None = None


class WorkspacePatch(BaseModel):
    name: str | None = None
    timezone: str | None = None


@router.patch("/settings/profile")
async def patch_profile(body: ProfilePatch, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return {"ok": True}


@router.patch("/settings/workspace")
async def patch_workspace(body: WorkspacePatch, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.workspaces.update_one({"id": ws(user)}, {"$set": updates})
    return {"ok": True}


@router.get("/audit")
async def audit_events(user: dict = Depends(get_current_user)):
    return await db.audit_events.find({"workspace_id": ws(user)}, {"_id": 0}).sort("created_at", -1).to_list(100)
# ----------------------------- OPPORTUNITIES -----------------------------
class OpportunityBody(BaseModel):
    tender_id: str
    tender_name: str
    estimated_value: float = 0.0
    req_capital: float = 0.0
    req_estimators: int = 0
    req_specialists: int = 0
    req_project_managers: int = 0
    status: str = "Evaluating"  # Evaluating, Bidding, Portfolio
    risk_score: int = 0
    qualification_score: int = 0

@router.get("/opportunities")
async def list_opportunities(user: dict = Depends(get_current_user)):
    return await db.opportunities.find({"workspace_id": ws(user)}, {"_id": 0}).sort("created_at", -1).to_list(100)

@router.post("/opportunities")
async def create_opportunity(body: OpportunityBody, user: dict = Depends(get_current_user)):
    w = ws(user)
    oid = uuid.uuid4().hex
    doc = {
        "id": oid,
        "workspace_id": w,
        **body.model_dump(),
        "created_at": now_iso()
    }
    await db.opportunities.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.patch("/opportunities/{oid}")
async def update_opportunity(oid: str, body: OpportunityBody, user: dict = Depends(get_current_user)):
    w = ws(user)
    op = await db.opportunities.find_one({"id": oid, "workspace_id": w})
    if not op:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    await db.opportunities.update_one({"id": oid}, {"$set": body.model_dump()})
    return await db.opportunities.find_one({"id": oid}, {"_id": 0})

@router.delete("/opportunities/{oid}")
async def delete_opportunity(oid: str, user: dict = Depends(get_current_user)):
    op = await db.opportunities.find_one({"id": oid, "workspace_id": ws(user)})
    if not op:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    await db.opportunities.delete_one({"id": oid})
    return {"ok": True}

# ----------------------------- PORTFOLIO & SCENARIOS -----------------------------
class OptimizeRequest(BaseModel):
    opportunity_ids: list[str]
    overrides: dict = {}

@router.post("/portfolio/optimize")
async def optimize_portfolio_route(body: OptimizeRequest, user: dict = Depends(get_current_user)):
    w = ws(user)
    company = await db.companies.find_one({"workspace_id": w}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=400, detail="Company profile not found.")
    
    opportunities = await db.opportunities.find({"id": {"$in": body.opportunity_ids}, "workspace_id": w}, {"_id": 0}).to_list(100)
    
    result = optimize_portfolio(opportunities, company, overrides=body.overrides)
    return result

@router.get("/portfolio/conflicts")
async def get_portfolio_conflicts(user: dict = Depends(get_current_user)):
    w = ws(user)
    company = await db.companies.find_one({"workspace_id": w}, {"_id": 0})
    if not company:
        return {"conflicts": []}
    
    # Get all opportunities currently in 'Portfolio' or 'Bidding' status
    active_opps = await db.opportunities.find(
        {"workspace_id": w, "status": {"$in": ["Portfolio", "Bidding"]}},
        {"_id": 0}
    ).to_list(100)
    
    from ai.portfolio import check_feasibility
    is_feasible, conflicts = check_feasibility(active_opps, company)
    return {"conflicts": conflicts}

@router.post("/analyses/{aid}/to-opportunity")
async def analysis_to_opportunity(aid: str, user: dict = Depends(get_current_user)):
    w = ws(user)
    a = await db.analyses.find_one({"id": aid, "workspace_id": w})
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found.")
        
    existing = await db.opportunities.find_one({"analysis_id": aid, "workspace_id": w})
    if existing:
        return {"created": False, "opportunity": existing}
        
    d = a.get("decision", {})
    # AI-inferred values could be derived here, but we'll use defaults and let user edit
    oid = uuid.uuid4().hex
    doc = {
        "id": oid,
        "workspace_id": w,
        "analysis_id": aid,
        "tender_id": a.get("tender_document_id", ""),
        "tender_name": a.get("tender_name", ""),
        "estimated_value": 0.0,
        "req_capital": 0.0,
        "req_estimators": 1,
        "req_specialists": 0,
        "req_project_managers": 1,
        "status": "Evaluating",
        "risk_score": d.get("risk", 50),
        "qualification_score": d.get("readiness_score", 50),
        "created_at": now_iso()
    }
    await db.opportunities.insert_one(doc)
    doc.pop("_id", None)
    return {"created": True, "opportunity": doc}

class ScenarioBody(BaseModel):
    name: str
    overrides: dict

@router.get("/scenarios")
async def list_scenarios(user: dict = Depends(get_current_user)):
    return await db.scenarios.find({"workspace_id": ws(user)}, {"_id": 0}).to_list(100)

@router.post("/scenarios")
async def create_scenario(body: ScenarioBody, user: dict = Depends(get_current_user)):
    w = ws(user)
    sid = uuid.uuid4().hex
    doc = {
        "id": sid,
        "workspace_id": w,
        **body.model_dump(),
        "created_at": now_iso()
    }
    await db.scenarios.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.delete("/scenarios/{sid}")
async def delete_scenario(sid: str, user: dict = Depends(get_current_user)):
    s = await db.scenarios.find_one({"id": sid, "workspace_id": ws(user)})
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    await db.scenarios.delete_one({"id": sid})
    return {"ok": True}

