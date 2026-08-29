"""Seeds a realistic demo workspace (idempotent). This is clearly-labelled DEMO data."""
import os
from datetime import datetime, timezone, timedelta

from core.db import db
from core.auth import hash_password

DEMO_USER_ID = "demo-user-0001"
DEMO_WS_ID = "demo-ws-0001"
DEMO_COMPANY_ID = "demo-company-0001"
DEMO_TENDER_DOC_ID = "demo-tender-doc-0001"
DEMO_ANALYSIS_ID = "demo-analysis-0001"


def _iso(dt):
    return dt.isoformat()


def now():
    return datetime.now(timezone.utc)


def _pages(paras):
    return [{"page_number": i + 1, "text": t} for i, t in enumerate(paras)]


async def seed_demo():
    if await db.users.find_one({"id": DEMO_USER_ID}):
        return  # already seeded

    demo_email = os.environ.get("DEMO_EMAIL", "demo@bidpilot.io")
    demo_pw = os.environ.get("DEMO_PASSWORD", "demo1234")

    await db.users.insert_one({
        "id": DEMO_USER_ID, "email": demo_email, "password_hash": hash_password(demo_pw),
        "name": "Ravi Menon", "role": "Owner", "workspace_id": DEMO_WS_ID,
        "avatar_initials": "RM", "is_demo": True, "created_at": _iso(now()),
    })

    await db.workspaces.insert_one({
        "id": DEMO_WS_ID, "name": "ABC Infrastructure — Bids", "owner_id": DEMO_USER_ID,
        "timezone": "Asia/Kolkata", "plan": "Professional", "created_at": _iso(now()),
    })

    await db.workspace_members.insert_many([
        {"id": "wm-1", "workspace_id": DEMO_WS_ID, "user_id": DEMO_USER_ID, "name": "Ravi Menon",
         "email": demo_email, "role": "Owner", "status": "Active", "last_activity": _iso(now())},
        {"id": "wm-2", "workspace_id": DEMO_WS_ID, "user_id": "u-2", "name": "Priya Nair",
         "email": "priya@abcinfra.in", "role": "Bid Manager", "status": "Active",
         "last_activity": _iso(now() - timedelta(hours=5))},
        {"id": "wm-3", "workspace_id": DEMO_WS_ID, "user_id": "u-3", "name": "Arjun Rao",
         "email": "arjun@abcinfra.in", "role": "Member", "status": "Invited",
         "last_activity": None},
    ])

    await db.companies.insert_one({
        "id": DEMO_COMPANY_ID, "workspace_id": DEMO_WS_ID,
        "legal_name": "ABC Infrastructure Pvt Ltd", "registration": "U45200KA2017PTC101234",
        "location": "Bengaluru, Karnataka", "years_experience": 8, "turnover": "₹42 Cr",
        "specialization": "Highway, Bridge & Elevated Corridor Construction",
        "readiness": 76, "created_at": _iso(now()),
        "registrations": [
            {"name": "PWD Class I Contractor", "number": "PWD/KA/CL1/2019/0456", "valid_till": "2027-03-31"},
            {"name": "GST Registration", "number": "29ABCDE1234F1Z5", "valid_till": None},
            {"name": "PF / ESIC", "number": "KA/BNG/0056789", "valid_till": None},
        ],
        "certifications": [
            {"name": "ISO 9001:2015", "number": "IN-QMS-88213", "expiry": "unclear", "status": "NEEDS_REVIEW"},
            {"name": "ISO 14001:2015", "number": "IN-EMS-44190", "expiry": "2026-11-30", "status": "PASS"},
        ],
    })

    await db.company_projects.insert_many([
        {"id": "prj-1", "company_id": DEMO_COMPANY_ID, "name": "NH-275 Widening Package 3",
         "client": "NHAI", "project_type": "Highway", "contract_value": "₹138 Cr",
         "completion_date": "2022-08-15", "location": "Mysuru, Karnataka",
         "description": "4-laning of 22 km stretch including 3 minor bridges."},
        {"id": "prj-2", "company_id": DEMO_COMPANY_ID, "name": "Hebbal Elevated Corridor Ramp",
         "client": "KRDCL", "project_type": "Elevated Corridor", "contract_value": "₹96 Cr",
         "completion_date": "2023-12-02", "location": "Bengaluru, Karnataka",
         "description": "Elevated ramp with segmental box girders, 1.8 km."},
        {"id": "prj-3", "company_id": DEMO_COMPANY_ID, "name": "Tumakuru Road Overbridge",
         "client": "PWD Karnataka", "project_type": "Bridge", "contract_value": "₹8.4 Cr",
         "completion_date": "2021-05-20", "location": "Tumakuru, Karnataka",
         "description": "ROB over railway line — below the ₹10 Cr similar-work threshold."},
    ])

    await db.company_personnel.insert_many([
        {"id": "per-1", "company_id": DEMO_COMPANY_ID, "name": "S. Venkatesh", "role": "Project Manager",
         "qualification": "B.Tech Civil", "experience": "12 years", "relevant": "3 metro/elevated corridor projects"},
        {"id": "per-2", "company_id": DEMO_COMPANY_ID, "name": "M. Fernandes", "role": "Quality Manager",
         "qualification": "M.Tech Structures", "experience": "9 years", "relevant": "QA/QC on 2 NHAI highways"},
    ])

    await db.company_equipment.insert_many([
        {"id": "eq-1", "company_id": DEMO_COMPANY_ID, "name": "Concrete Batching Plant",
         "capacity": "45 m³/hr", "ownership": "Owned", "availability": "Available"},
        {"id": "eq-2", "company_id": DEMO_COMPANY_ID, "name": "Crawler Crane 80T",
         "capacity": "80 T", "ownership": "Owned", "availability": "Available"},
        {"id": "eq-3", "company_id": DEMO_COMPANY_ID, "name": "Launching Girder",
         "capacity": "40 m span", "ownership": "Leased", "availability": "On request"},
    ])

    # ---- Company documents (with page text so RAG works for future analyses too) ----
    cdocs = [
        ("cd-1", "Company Profile 2024.pdf", "Company Profile", "Verified", None,
         ["ABC Infrastructure Pvt Ltd. Incorporated 2017 (8 years). CIN U45200KA2017PTC101234. "
          "Specialization: highway, bridge and elevated corridor construction. Head office Bengaluru, Karnataka."]),
        ("cd-2", "Audited Financials FY22-FY24.pdf", "Financial", "Verified", "2025-09-30",
         ["Audited turnover FY2021-22 ₹36 Cr, FY2022-23 ₹41 Cr, FY2023-24 ₹49 Cr. "
          "Average annual turnover last three years ₹42 Cr. Net worth positive, solvency certificate attached."]),
        ("cd-3", "Experience Certificates.pdf", "Experience", "Verified", None,
         ["Completion certificate NH-275 Widening Package 3, NHAI, ₹138 Cr, completed Aug 2022. "
          "Completion certificate Hebbal Elevated Corridor Ramp, KRDCL, ₹96 Cr, completed Dec 2023. "
          "Two completed similar works above ₹10 Cr. A third ROB project was ₹8.4 Cr (below threshold)."]),
        ("cd-4", "PWD Class I Registration.pdf", "Registration", "Verified", "2027-03-31",
         ["PWD Karnataka Class I civil contractor registration PWD/KA/CL1/2019/0456, valid till 31 March 2027."]),
        ("cd-5", "ISO 9001 Certificate.pdf", "Certification", "Needs Review", None,
         ["ISO 9001:2015 Quality Management System certificate IN-QMS-88213 issued to ABC Infrastructure. "
          "Certificate scan is faint; the expiry/validity date could not be reliably read from the document."]),
        ("cd-6", "Key Personnel CVs.pdf", "Personnel", "Processed", None,
         ["S. Venkatesh, Project Manager, B.Tech Civil, 12 years experience across metro and elevated corridor works. "
          "M. Fernandes, Quality Manager, M.Tech Structures, 9 years."]),
        ("cd-7", "Equipment Schedule.pdf", "Equipment", "Processed", None,
         ["Owned concrete batching plant capacity 45 m³/hr. Crawler crane 80T owned. Launching girder 40m leased."]),
    ]
    docs_to_insert = []
    for did, fname, cat, vstate, expiry, paras in cdocs:
        docs_to_insert.append({
            "id": did, "workspace_id": DEMO_WS_ID, "company_id": DEMO_COMPANY_ID,
            "doc_type": "company", "filename": fname, "category": cat,
            "size": 240000, "page_count": len(paras), "status": "Processed",
            "verification_state": vstate, "expiry": expiry, "storage_path": None,
            "pages": _pages(paras), "created_at": _iso(now() - timedelta(days=20)),
        })
    await db.documents.insert_many(docs_to_insert)

    # ---- Tender document ----
    tender_pages = _pages([
        "Bengaluru Metro Corridor-7 — Civil Works Package C4. Notice Inviting Tender (NIT). "
        "Bangalore Metro Rail Corporation Ltd (BMRCL). Estimated cost ₹412 Cr.",
        "Section II Eligibility. Bidder must have average annual financial turnover of ₹30 Cr during the last "
        "three financial years. Bidder must have minimum 5 years experience in civil construction.",
        "The bidder must have successfully completed three similar completed projects each above ₹10 Cr in the "
        "last seven years. Similar work means elevated corridor / bridge / viaduct civil works.",
        "Bidder must hold valid contractor registration of PWD Class I or equivalent. A valid ISO 9001 quality "
        "certificate is required and must be enclosed with the technical bid.",
        "Bid security (EMD) of ₹85,00,000 shall be furnished by bank guarantee valid for 180 days.",
        "Key personnel: Project Manager must be B.Tech Civil with minimum 10 years relevant experience. "
        "Concrete batching plant of minimum 30 m³/hr capacity must be deployed at site.",
        "Compliance documents to be submitted: GST registration, latest audited financial statements, experience "
        "certificates, PWD license, Power of Attorney, Bank Guarantee for EMD, Affidavit of Non-Blacklisting, and a "
        "signed Technical Declaration.",
        "Completion period is 24 months. Liquidated damages of 0.5% of contract value per week of delay up to a "
        "maximum of 10%. The contract is fixed-price with no price escalation permitted.",
        "Working hours at site are restricted to 10:00 to 18:00 on account of traffic management near the corridor. "
        "Site access is constrained and shared with an operational road.",
        "Key dates: Pre-bid meeting 12 Aug 2025. Deadline for clarifications 20 Aug 2025. Bid submission deadline "
        "10 Sep 2025 15:00. Technical bid opening 11 Sep 2025.",
    ])
    await db.documents.insert_one({
        "id": DEMO_TENDER_DOC_ID, "workspace_id": DEMO_WS_ID, "company_id": None,
        "doc_type": "tender", "filename": "Metro-Corridor7-Tender.pdf", "category": "Tender",
        "size": 25795788, "page_count": 187, "status": "Processed", "verification_state": None,
        "expiry": None, "storage_path": None, "pages": tender_pages,
        "created_at": _iso(now() - timedelta(days=3)),
    })

    # ---- Requirements (seeded demo findings) ----
    def req(cat, name, tender_req, company_ev, status, conf, doc, page, expl):
        import uuid
        return {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "category": cat,
                "name": name, "description": tender_req, "tender_requirement": tender_req,
                "company_evidence": company_ev, "status": status, "confidence": conf,
                "source_page": page, "evidence_source_document": doc, "evidence_source_page": page,
                "explanation": expl, "evidence_chunks": []}

    requirements = [
        req("Financial", "Average annual turnover", "Average annual turnover of ₹30 Cr over last 3 years",
            "Average annual turnover ₹42 Cr (FY22 ₹36 Cr, FY23 ₹41 Cr, FY24 ₹49 Cr)", "PASS", 96,
            "Audited Financials FY22-FY24.pdf", 2, "Company turnover ₹42 Cr comfortably exceeds the ₹30 Cr requirement."),
        req("Eligibility", "Minimum experience", "Minimum 5 years experience in civil construction",
            "8 years in operation with relevant civil works", "PASS", 94,
            "Company Profile 2024.pdf", 2, "8 years exceeds the 5-year minimum."),
        req("Eligibility", "Similar completed projects", "3 similar completed projects above ₹10 Cr",
            "Only 2 qualifying projects above ₹10 Cr found (₹138 Cr, ₹96 Cr); third was ₹8.4 Cr", "FAIL", 88,
            "Experience Certificates.pdf", 3, "Requirement asks for 3 similar works above ₹10 Cr; only 2 qualify. This is a blocker."),
        req("Eligibility", "Contractor registration", "Valid PWD Class I registration or equivalent",
            "PWD Class I registration PWD/KA/CL1/2019/0456 valid till 2027", "PASS", 97,
            "PWD Class I Registration.pdf", 4, "Valid PWD Class I registration on record."),
        req("Compliance", "ISO 9001 certificate", "Valid ISO 9001 certificate enclosed with technical bid",
            "ISO 9001 certificate found but expiry/validity could not be reliably confirmed", "NEEDS_REVIEW", 55,
            "ISO 9001 Certificate.pdf", 4, "Certificate exists but its validity date is unreadable — confirm before submission."),
        req("Compliance", "Bid security (EMD)", "Bid security of ₹85,00,000 via bank guarantee, 180 days validity",
            "No bank guarantee for EMD on file", "NEEDS_REVIEW", 60,
            None, 5, "EMD bank guarantee has not yet been arranged."),
        req("Personnel", "Project Manager qualification", "Project Manager: B.Tech Civil + 10+ years",
            "S. Venkatesh — B.Tech Civil, 12 years relevant experience", "PASS", 92,
            "Key Personnel CVs.pdf", 6, "Nominated PM exceeds the qualification and experience requirement."),
        req("Equipment", "Batching plant capacity", "Concrete batching plant minimum 30 m³/hr",
            "Owned batching plant 45 m³/hr", "PASS", 95,
            "Equipment Schedule.pdf", 6, "Owned plant capacity 45 m³/hr exceeds 30 m³/hr minimum."),
        req("Compliance", "Bank Guarantee document", "Bank Guarantee for EMD to be submitted",
            "Not found in company documents", "FAIL", 80,
            None, 7, "Required submission document is missing."),
        req("Compliance", "Affidavit of Non-Blacklisting", "Signed affidavit of non-blacklisting required",
            "Not found in company documents", "FAIL", 80,
            None, 7, "Required submission document is missing."),
        req("Compliance", "Technical Declaration", "Signed Technical Declaration required",
            "Not prepared yet", "NEEDS_REVIEW", 50,
            None, 7, "Standard declaration to be drafted and signed."),
    ]
    await db.requirements.insert_many(requirements)

    # ---- Risks ----
    import uuid
    risks = [
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "severity": "HIGH",
         "title": "Aggressive completion timeline", "clause": "Completion period 24 months",
         "concern": "24 months for a ₹412 Cr elevated corridor package is tight given site constraints.",
         "impact": "Risk of schedule overrun triggering liquidated damages.", "source_page": 8},
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "severity": "HIGH",
         "title": "Liquidated damages exposure", "clause": "LD 0.5%/week up to 10%",
         "concern": "LD capped at 10% of contract value is a material financial exposure.",
         "impact": "Up to ₹41 Cr exposure on delay.", "source_page": 8},
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "severity": "MEDIUM",
         "title": "Fixed-price / no escalation", "clause": "Fixed-price, no price escalation permitted",
         "concern": "No escalation over 24 months exposes the bid to input-cost inflation.",
         "impact": "Margin erosion if steel/cement prices rise.", "source_page": 8},
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "severity": "MEDIUM",
         "title": "Restricted working hours & site access", "clause": "Working hours 10:00-18:00",
         "concern": "Restricted hours and shared road access reduce productive working time.",
         "impact": "Lower daily output; schedule pressure.", "source_page": 9},
    ]
    await db.risks.insert_many(risks)

    # ---- Action items ----
    actions = [
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "title": "Obtain a third qualifying project certificate",
         "reason": "Only 2 of 3 required similar works above ₹10 Cr are evidenced.", "priority": "HIGH",
         "source": "Requirement · Eligibility", "status": "OPEN"},
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "title": "Arrange bid security (EMD) bank guarantee",
         "reason": "₹85,00,000 BG valid 180 days is required with the bid.", "priority": "HIGH",
         "source": "Requirement · Compliance", "status": "OPEN"},
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "title": "Confirm ISO 9001 certificate validity",
         "reason": "Certificate found but expiry could not be confirmed.", "priority": "MEDIUM",
         "source": "Requirement · Compliance", "status": "OPEN"},
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "title": "Prepare Affidavit of Non-Blacklisting",
         "reason": "Mandatory submission document is missing.", "priority": "HIGH",
         "source": "Requirement · Compliance", "status": "OPEN"},
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "title": "Complete signed Technical Declaration",
         "reason": "Required declaration not yet drafted.", "priority": "MEDIUM",
         "source": "Requirement · Compliance", "status": "OPEN"},
        {"id": uuid.uuid4().hex, "analysis_id": DEMO_ANALYSIS_ID, "title": "Review LD and completion-timeline clause with estimation team",
         "reason": "High LD cap combined with a tight schedule.", "priority": "MEDIUM",
         "source": "Risk analysis", "status": "OPEN"},
    ]
    await db.action_items.insert_many(actions)

    decision = {
        "outcome": "BID WITH CONDITIONS", "readiness_score": 76,
        "eligibility": 82, "compliance": 60, "technical": 92, "risk": 68,
        "satisfied_items": 5, "blockers": 3, "review_items": 3,
        "recommendation": ("This tender is within ABC Infrastructure's capability, but three conditions must be "
                           "closed before submission: a third qualifying project reference, the EMD bank guarantee, "
                           "and the missing compliance affidavits/declaration. Confirm ISO 9001 validity and review "
                           "the LD/timeline exposure with the estimation team."),
    }
    deadlines = [
        {"label": "Pre-bid meeting", "date": "2025-08-12", "source_page": 10},
        {"label": "Clarification deadline", "date": "2025-08-20", "source_page": 10},
        {"label": "Submission deadline", "date": "2025-09-10", "source_page": 10},
        {"label": "Technical bid opening", "date": "2025-09-11", "source_page": 10},
    ]

    await db.analyses.insert_one({
        "id": DEMO_ANALYSIS_ID, "workspace_id": DEMO_WS_ID, "company_id": DEMO_COMPANY_ID,
        "company_name": "ABC Infrastructure Pvt Ltd",
        "tender_name": "Bengaluru Metro Corridor-7 — Civil Works Package C4",
        "tender_document_id": DEMO_TENDER_DOC_ID, "evidence_document_ids": [d[0] for d in cdocs],
        "status": "completed", "stage_index": 9, "stage_label": "Completed",
        "decision": decision, "deadlines": deadlines,
        "created_at": _iso(now() - timedelta(days=2)), "updated_at": _iso(now() - timedelta(days=2)),
        "completed_at": _iso(now() - timedelta(days=2)), "error": None, "is_demo": True,
    })

    # ---- Notifications ----
    await db.notifications.insert_many([
        {"id": "n-1", "workspace_id": DEMO_WS_ID, "type": "analysis_complete",
         "title": "Analysis complete", "message": "Bengaluru Metro Corridor-7 — BID WITH CONDITIONS (76% ready)",
         "read": False, "created_at": _iso(now() - timedelta(days=2))},
        {"id": "n-2", "workspace_id": DEMO_WS_ID, "type": "deadline",
         "title": "Tender deadline approaching", "message": "Corridor-7 submission deadline 10 Sep 2025",
         "read": False, "created_at": _iso(now() - timedelta(days=1))},
        {"id": "n-3", "workspace_id": DEMO_WS_ID, "type": "document_expiring",
         "title": "Document needs review", "message": "ISO 9001 certificate validity could not be confirmed",
         "read": True, "created_at": _iso(now() - timedelta(hours=8))},
    ])

    # ---- Billing: plans, subscription, invoices, usage ----
    await db.plans.insert_many([
        {"id": "plan-starter", "name": "Starter", "price": 49, "currency": "USD", "period": "month",
         "analyses": 5, "storage_gb": 5, "users": 2,
         "features": ["5 analyses / month", "5 GB storage", "2 users", "Standard analysis", "Email support"]},
        {"id": "plan-pro", "name": "Professional", "price": 199, "currency": "USD", "period": "month",
         "analyses": 30, "storage_gb": 50, "users": 10,
         "features": ["30 analyses / month", "50 GB storage", "10 users", "Advanced analysis",
                      "Evidence retention 12 months", "Team collaboration", "Priority support"]},
        {"id": "plan-business", "name": "Business", "price": 599, "currency": "USD", "period": "month",
         "analyses": 150, "storage_gb": 250, "users": 50,
         "features": ["150 analyses / month", "250 GB storage", "50 users", "Advanced analysis",
                      "Evidence retention 36 months", "Audit trail export", "SSO", "Dedicated support"]},
    ])
    await db.subscriptions.insert_one({
        "id": "sub-1", "workspace_id": DEMO_WS_ID, "plan_id": "plan-pro", "plan_name": "Professional",
        "status": "active", "billing_cycle": "monthly", "next_billing_date": _iso(now() + timedelta(days=17)),
        "payment_method": {"brand": "Visa", "last4": "4242", "exp": "08/27"}, "sandbox": True,
        "created_at": _iso(now() - timedelta(days=90))},)
    await db.usage_records.insert_one({
        "id": "usage-1", "workspace_id": DEMO_WS_ID, "period": "current",
        "analyses_used": 7, "analyses_limit": 30, "storage_used_gb": 11.4, "storage_limit_gb": 50,
        "users_used": 3, "users_limit": 10})
    await db.invoices.insert_many([
        {"id": "inv-1003", "workspace_id": DEMO_WS_ID, "number": "BP-2025-1003", "amount": 199,
         "currency": "USD", "status": "Paid", "date": _iso(now() - timedelta(days=13)), "period": "Aug 2025"},
        {"id": "inv-1002", "workspace_id": DEMO_WS_ID, "number": "BP-2025-1002", "amount": 199,
         "currency": "USD", "status": "Paid", "date": _iso(now() - timedelta(days=43)), "period": "Jul 2025"},
        {"id": "inv-1001", "workspace_id": DEMO_WS_ID, "number": "BP-2025-1001", "amount": 199,
         "currency": "USD", "status": "Paid", "date": _iso(now() - timedelta(days=73)), "period": "Jun 2025"},
    ])

    await db.audit_events.insert_many([
        {"id": "ae-1", "workspace_id": DEMO_WS_ID, "actor": "Ravi Menon", "event": "analysis_completed",
         "detail": "Corridor-7 analysis completed — BID WITH CONDITIONS", "created_at": _iso(now() - timedelta(days=2))},
        {"id": "ae-2", "workspace_id": DEMO_WS_ID, "actor": "Priya Nair", "event": "document_uploaded",
         "detail": "Uploaded Metro-Corridor7-Tender.pdf", "created_at": _iso(now() - timedelta(days=3))},
        {"id": "ae-3", "workspace_id": DEMO_WS_ID, "actor": "Ravi Menon", "event": "login",
         "detail": "Signed in", "created_at": _iso(now() - timedelta(days=3, hours=1))},
    ])
