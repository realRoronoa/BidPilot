"""Orchestrates the full AI analysis pipeline as a background job."""
import asyncio
import traceback
import uuid
from datetime import datetime, timezone

from core.db import db
from core.decision import synthesize_decision
from rag.pipeline import chunk_pages
from rag.embeddings import attach_embeddings
from ai.pipeline import (
    extract_requirements, match_requirement, analyze_risks, build_action_items,
)

STAGES = [
    "Reading tender documents",
    "Extracting requirements",
    "Identifying eligibility criteria",
    "Matching company qualifications",
    "Checking compliance requirements",
    "Analyzing technical requirements",
    "Analyzing commercial/project risks",
    "Verifying evidence",
    "Preparing recommendation",
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def _set_stage(analysis_id, stage_index, status="running"):
    await db.analyses.update_one(
        {"id": analysis_id},
        {"$set": {"stage_index": stage_index, "status": status,
                  "stage_label": STAGES[stage_index] if stage_index < len(STAGES) else "Done",
                  "updated_at": now_iso()}},
    )


async def _company_chunks(workspace_id, company_id, document_ids):
    query = {"workspace_id": workspace_id, "doc_type": "company"}
    if document_ids:
        query["id"] = {"$in": document_ids}
    docs = await db.documents.find(query, {"_id": 0}).to_list(200)
    chunks = []
    for d in docs:
        pages = d.get("pages") or []
        chunks.extend(chunk_pages(pages, d["id"], "company", d["filename"]))
    return chunks


async def run_analysis(analysis_id):
    try:
        analysis = await db.analyses.find_one({"id": analysis_id}, {"_id": 0})
        if not analysis:
            return
        workspace_id = analysis["workspace_id"]

        await _set_stage(analysis_id, 0)
        tender_doc = await db.documents.find_one(
            {"id": analysis["tender_document_id"]}, {"_id": 0})
        if not tender_doc:
            raise RuntimeError("Tender document could not be found.")
            
        tender_chunks = await db.document_chunks.find({"document_id": analysis["tender_document_id"]}, {"_id": 0}).to_list(1000)
        if not tender_chunks:
            # Fallback if chunks weren't saved for some reason
            if not tender_doc.get("pages"):
                raise RuntimeError("Tender document could not be read (no extractable text). "
                                   "The file may be scanned or corrupted.")
            tender_chunks = chunk_pages(tender_doc["pages"], tender_doc["id"], "tender", tender_doc["filename"])
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, attach_embeddings, tender_chunks)

        company = await db.companies.find_one({"id": analysis["company_id"]}, {"_id": 0})
        company_summary = ""
        if company:
            company_summary = (f"{company.get('legal_name')} | {company.get('specialization')} | "
                               f"{company.get('years_experience')} yrs | Turnover {company.get('turnover')}")

        await _set_stage(analysis_id, 1)
        requirements, deadlines = await extract_requirements(tender_chunks, company_summary)
        if not requirements:
            raise RuntimeError("No requirements could be extracted from the tender.")

        await _set_stage(analysis_id, 2)
        company_chunks = await _company_chunks(
            workspace_id, analysis["company_id"], analysis.get("evidence_document_ids"))
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, attach_embeddings, company_chunks)

        await _set_stage(analysis_id, 3)
        matched = []
        # match concurrently in small batches to stay within time budget
        for i in range(0, len(requirements), 4):
            batch = requirements[i:i + 4]
            results = await asyncio.gather(*[match_requirement(r, company_chunks) for r in batch])
            matched.extend(results)
            if i == 0:
                await _set_stage(analysis_id, 4)

        await _set_stage(analysis_id, 5)
        await _set_stage(analysis_id, 6)
        risks = await analyze_risks(tender_chunks)

        await _set_stage(analysis_id, 7)
        action_items = build_action_items(matched, risks)

        await _set_stage(analysis_id, 8)
        decision = synthesize_decision(matched, risks)

        # persist
        await db.requirements.delete_many({"analysis_id": analysis_id})
        await db.risks.delete_many({"analysis_id": analysis_id})
        await db.action_items.delete_many({"analysis_id": analysis_id})
        if matched:
            await db.requirements.insert_many([{**m, "analysis_id": analysis_id} for m in matched])
        if risks:
            await db.risks.insert_many([{**r, "analysis_id": analysis_id} for r in risks])
        if action_items:
            await db.action_items.insert_many([{**a, "analysis_id": analysis_id} for a in action_items])

        await db.analyses.update_one(
            {"id": analysis_id},
            {"$set": {
                "status": "completed", "stage_index": len(STAGES),
                "stage_label": "Completed", "decision": decision,
                "deadlines": deadlines, "completed_at": now_iso(), "updated_at": now_iso(),
                "error": None,
            }},
        )
        await db.notifications.insert_one({
            "id": uuid.uuid4().hex, "workspace_id": workspace_id,
            "type": "analysis_complete", "title": "Analysis complete",
            "message": f"{analysis['tender_name']} — {decision['outcome']} ({decision['readiness_score']}% ready)",
            "read": False, "created_at": now_iso(),
        })
    except Exception as e:
        traceback.print_exc()
        await db.analyses.update_one(
            {"id": analysis_id},
            {"$set": {"status": "failed", "error": str(e), "updated_at": now_iso()}},
        )
        analysis = await db.analyses.find_one({"id": analysis_id}, {"_id": 0})
        if analysis:
            await db.notifications.insert_one({
                "id": uuid.uuid4().hex, "workspace_id": analysis["workspace_id"],
                "type": "analysis_failed", "title": "Analysis failed",
                "message": f"{analysis['tender_name']} — {str(e)[:140]}",
                "read": False, "created_at": now_iso(),
            })
