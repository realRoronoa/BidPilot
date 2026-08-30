"""AI analysis pipeline using Claude Sonnet 4.6 via Emergent Universal Key.

Modular agents: requirement extraction, evidence matching, risk analysis.
Every agent is instructed with strict anti-hallucination rules. The model
returns structured JSON which we validate before use. The final decision is
NOT chosen by the model - it is computed deterministically in core.decision.
"""
import os
import json
import uuid
import re

import asyncio
import requests

from rag.embeddings import semantic_retrieve

MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-6"

ANTI_HALLUCINATION = (
    "STRICT RULES: Never invent tender clauses, company capabilities, certifications, projects, "
    "financial values, or page numbers. Only use the text provided. If evidence is missing, say so. "
    "If a value is unclear, mark NEEDS_REVIEW. Always cite the page number from the provided source text. "
    "Return ONLY valid JSON, no markdown fences, no commentary."
)


class UserMessage:
    def __init__(self, text: str):
        self.text = text


class LlmChat:
    def __init__(self, api_key: str, session_id: str, system_message: str):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.provider = MODEL_PROVIDER
        self.model = MODEL_NAME
        self.gateway_url = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip().rstrip("/") or "https://integrations.emergentagent.com"

    def with_model(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        return self

    async def send_message(self, message: UserMessage) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_sync, message.text)

    def _send_sync(self, user_text: str) -> str:
        # 1. Emergent Gateway
        gateway_endpoint = f"{self.gateway_url}/llm/api/v1/chat"
        payload = {
            "emergent_key": self.api_key,
            "session_id": self.session_id,
            "system_message": self.system_message,
            "provider": self.provider,
            "model": self.model,
            "messages": [{"role": "user", "content": user_text}],
        }
        try:
            resp = requests.post(gateway_endpoint, json=payload, timeout=90)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    return data.get("response") or data.get("content") or data.get("text") or json.dumps(data)
                return str(data)
            else:
                print(f"Emergent Gateway returned {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"Emergent Gateway failed: {e}")

        # 2. Anthropic Direct fallback
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or (self.api_key if self.api_key.startswith("sk-ant-") else None)
        if anthropic_key:
            headers = {"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            p = {
                "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                "max_tokens": 4096,
                "system": self.system_message,
                "messages": [{"role": "user", "content": user_text}],
            }
            r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=p, timeout=90)
            r.raise_for_status()
            data = r.json()
            return "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")

        # 3. OpenAI Direct fallback
        openai_key = os.environ.get("OPENAI_API_KEY") or (self.api_key if (self.api_key.startswith("sk-") and not self.api_key.startswith("sk-emergent-")) else None)
        if openai_key:
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            p = {
                "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
                "messages": [{"role": "system", "content": self.system_message}, {"role": "user", "content": user_text}],
            }
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=p, timeout=90)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

        raise RuntimeError("Could not connect to LLM gateway. Please ensure EMERGENT_LLM_KEY is configured.")


def _new_chat(system_message: str) -> LlmChat:
    return LlmChat(
        api_key=os.environ.get("EMERGENT_LLM_KEY", ""),
        session_id=f"bidpilot-{uuid.uuid4()}",
        system_message=system_message,
    ).with_model(MODEL_PROVIDER, MODEL_NAME)


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # find first { or [
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == opener:
                    depth += 1
                elif text[i] == closer:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break
    return json.loads(text)


async def _ask(system_message: str, user_text: str):
    chat = _new_chat(system_message)
    resp = await chat.send_message(UserMessage(text=user_text))
    return _extract_json(resp)


def _tender_context(tender_pages, max_chars=14000):
    """Build a page-tagged context string from the tender, truncated to budget."""
    parts = []
    used = 0
    for p in tender_pages:
        if not p["text"]:
            continue
        block = f"[PAGE {p['page_number']}]\n{p['text']}\n"
        if used + len(block) > max_chars:
            block = block[: max(0, max_chars - used)]
            parts.append(block)
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts)


async def extract_requirements(tender_chunks, company_summary):
    system = (
        "You are BidPilot's Requirement Extractor for construction tenders. "
        "Extract concrete, checkable requirements a bidder must satisfy. " + ANTI_HALLUCINATION
    )
    
    # RAG: Retrieve context specifically for requirements and deadlines
    queries = [
        "eligibility criteria criteria requirements",
        "financial turnover working capital",
        "technical experience similar projects",
        "personnel engineers project managers",
        "equipment machinery",
        "deadlines submission dates"
    ]
    
    retrieved = []
    seen = set()
    for q in queries:
        chunks = semantic_retrieve(q, tender_chunks, top_k=3)
        for c in chunks:
            text_id = f"{c['page_number']}-{c['text'][:20]}"
            if text_id not in seen:
                seen.add(text_id)
                retrieved.append(c)
                
    context = "\n\n".join(f"[PAGE {c['page_number']}]\n{c['text']}" for c in retrieved)
    
    prompt = f"""From the tender text below, extract every important requirement.
Categorize each into one of: Eligibility, Financial, Compliance, Technical, Personnel, Equipment.

For each requirement return an object:
{{"category": "...", "name": "short label", "description": "what the tender demands",
  "tender_requirement": "the specific threshold/condition", "source_page": <int page number from [PAGE n] tags>}}

Also extract key dates as a separate list.

Return JSON:
{{"requirements": [ ... up to 18 items ... ],
  "deadlines": [{{"label": "Submission deadline", "date": "as written or null", "source_page": <int>}}]}}

TENDER TEXT:
{context}
"""
    data = await _ask(system, prompt)
    reqs = data.get("requirements", []) if isinstance(data, dict) else []
    deadlines = data.get("deadlines", []) if isinstance(data, dict) else []
    cleaned = []
    for r in reqs:
        if not isinstance(r, dict) or not r.get("name"):
            continue
        cleaned.append({
            "id": str(uuid.uuid4()),
            "category": r.get("category", "Compliance"),
            "name": r.get("name", "")[:160],
            "description": r.get("description", ""),
            "tender_requirement": r.get("tender_requirement", ""),
            "source_page": r.get("source_page"),
        })
    return cleaned, deadlines


async def match_requirement(req, company_chunks):
    """Retrieve company evidence for a requirement and let the model judge PASS/FAIL/NEEDS_REVIEW."""
    query = f"{req['name']} {req['tender_requirement']} {req['description']}"
    evidence = semantic_retrieve(query, company_chunks, top_k=4)
    system = (
        "You are BidPilot's Evidence Matcher. Compare a tender requirement against retrieved company "
        "evidence and decide PASS, FAIL, or NEEDS_REVIEW. " + ANTI_HALLUCINATION
    )
    ev_text = "\n\n".join(
        f"[DOC: {e['filename']} | PAGE {e['page_number']}]\n{e['text']}" for e in evidence
    ) or "NO COMPANY EVIDENCE RETRIEVED."
    prompt = f"""TENDER REQUIREMENT:
Category: {req['category']}
Requirement: {req['tender_requirement'] or req['description']}

RETRIEVED COMPANY EVIDENCE:
{ev_text}

Decide status:
- PASS only if the evidence clearly satisfies the requirement.
- FAIL if the evidence clearly shows the requirement is NOT met.
- NEEDS_REVIEW if evidence is missing, incomplete, or unclear.

Return JSON:
{{"status": "PASS|FAIL|NEEDS_REVIEW", "confidence": <0-100 int>,
  "company_evidence": "what the company evidence shows (quote/paraphrase, no invention)",
  "explanation": "1-2 sentence justification",
  "evidence_source_document": "filename or null", "evidence_source_page": <int or null>}}"""
    try:
        data = await _ask(system, prompt)
    except Exception:
        data = {}
    status = data.get("status", "NEEDS_REVIEW")
    if status not in ("PASS", "FAIL", "NEEDS_REVIEW"):
        status = "NEEDS_REVIEW"
    src = evidence[0] if evidence else None
    return {
        **req,
        "status": status,
        "confidence": int(data.get("confidence", 50) or 50),
        "company_evidence": data.get("company_evidence", "No supporting evidence found."),
        "explanation": data.get("explanation", ""),
        "evidence_source_document": data.get("evidence_source_document") or (src["filename"] if src else None),
        "evidence_source_page": data.get("evidence_source_page") or (src["page_number"] if src else None),
        "evidence_chunks": evidence,
    }


async def analyze_risks(tender_chunks):
    system = (
        "You are BidPilot's Risk Analyzer for construction tenders. Identify commercial and project "
        "risks strictly from the tender text. " + ANTI_HALLUCINATION
    )
    
    queries = [
        "liquidated damages penalties delay",
        "payment terms retention money defect liability",
        "termination default disputes",
        "bid security performance bank guarantee"
    ]
    
    retrieved = []
    seen = set()
    for q in queries:
        chunks = semantic_retrieve(q, tender_chunks, top_k=4)
        for c in chunks:
            text_id = f"{c['page_number']}-{c['text'][:20]}"
            if text_id not in seen:
                seen.add(text_id)
                retrieved.append(c)
                
    context = "\n\n".join(f"[PAGE {c['page_number']}]\n{c['text']}" for c in retrieved)
    
    prompt = f"""Identify commercial/project risks from the tender text (schedule, liquidated damages,
price escalation, payment terms, site access, technical complexity, resources, contractual exposure).

Return JSON:
{{"risks": [{{"severity": "HIGH|MEDIUM|LOW", "title": "...", "clause": "the clause text or reference",
  "concern": "why it's risky", "impact": "commercial/project impact", "source_page": <int>}}]}}
Return up to 8 risks, most severe first.

TENDER TEXT:
{context}
"""
    try:
        data = await _ask(system, prompt)
        risks = data.get("risks", []) if isinstance(data, dict) else []
    except Exception:
        risks = []
    out = []
    for r in risks:
        if not isinstance(r, dict) or not r.get("title"):
            continue
        sev = r.get("severity", "MEDIUM")
        if sev not in ("HIGH", "MEDIUM", "LOW"):
            sev = "MEDIUM"
        out.append({
            "id": str(uuid.uuid4()),
            "severity": sev,
            "title": r.get("title", "")[:160],
            "clause": r.get("clause", ""),
            "concern": r.get("concern", ""),
            "impact": r.get("impact", ""),
            "source_page": r.get("source_page"),
        })
    return out


def build_action_items(requirements, risks):
    actions = []
    for r in requirements:
        if r["status"] == "FAIL":
            actions.append({
                "id": str(uuid.uuid4()), "title": f"Resolve blocker: {r['name']}",
                "reason": r.get("explanation") or r.get("tender_requirement", ""),
                "priority": "HIGH", "source": f"Requirement · {r['category']}", "status": "OPEN",
            })
        elif r["status"] == "NEEDS_REVIEW":
            actions.append({
                "id": str(uuid.uuid4()), "title": f"Review & confirm: {r['name']}",
                "reason": r.get("explanation") or "Evidence unclear or incomplete.",
                "priority": "MEDIUM", "source": f"Requirement · {r['category']}", "status": "OPEN",
            })
    for r in risks:
        if r["severity"] == "HIGH":
            actions.append({
                "id": str(uuid.uuid4()), "title": f"Mitigate risk: {r['title']}",
                "reason": r.get("concern", ""), "priority": "HIGH",
                "source": "Risk analysis", "status": "OPEN",
            })
    return actions


async def infer_resource_profile(tender_pages, decision):
    """Interpret a tender to estimate the bid resources it would consume. Labelled AI_INFERRED."""
    system = ("You are BidPilot's Resource Estimator. From a construction tender, estimate the bidding "
              "resources a mid-size contractor would need. " + ANTI_HALLUCINATION)
    context = _tender_context(tender_pages, max_chars=10000)
    prompt = f"""Estimate the resources required to prepare and deliver a bid for this tender.
Return JSON with integer/number fields (use conservative estimates, never invent exact figures you cannot infer):
{{"estimators": <int 1-4>, "engineers": <int 1-6>, "project_managers": <int 1-3>,
  "specialist_engineers": <int 0-2>, "capital_cr": <float ₹Cr working capital needed>,
  "bid_security_cr": <float ₹Cr EMD if stated else best estimate>, "bid_effort_days": <int>,
  "equipment": [{{"name": "...", "qty": <int>}}], "value_cr": <float contract value ₹Cr or null>}}

TENDER TEXT:
{context}
"""
    try:
        d = await _ask(system, prompt)
    except Exception:
        d = {}
    def _i(k, default): 
        try: return int(d.get(k, default))
        except Exception: return default
    def _f(k, default):
        try: return round(float(d.get(k, default)), 2)
        except Exception: return default
    equip = []
    for e in (d.get("equipment") or []):
        if isinstance(e, dict) and e.get("name"):
            try: equip.append({"name": e["name"][:60], "qty": int(e.get("qty", 1))})
            except Exception: pass
    rs = decision.get("risk", 100) if decision else 100
    risk = "LOW" if rs >= 75 else "MEDIUM" if rs >= 50 else "HIGH"
    return {
        "resources": {"estimators": _i("estimators", 1), "engineers": _i("engineers", 2),
                      "project_managers": _i("project_managers", 1),
                      "specialist_engineers": _i("specialist_engineers", 0),
                      "capital_cr": _f("capital_cr", 1.0), "bid_security_cr": _f("bid_security_cr", 0.3),
                      "bid_effort_days": _i("bid_effort_days", 8), "equipment": equip},
        "value_cr": _f("value_cr", None) if d.get("value_cr") is not None else None,
        "risk": risk,
    }


async def infer_capacity_from_evidence(company_chunks):
    """Suggest company capacity from uploaded evidence. All values labelled AI_INFERRED for review."""
    if not company_chunks:
        return None
    system = ("You are BidPilot's Capacity Assistant. From a company's own documents, estimate its bidding "
              "capacity. Only use what the documents imply. " + ANTI_HALLUCINATION)
    text = "\n\n".join(f"[{c['filename']}] {c['text']}" for c in company_chunks[:20])[:12000]
    prompt = f"""From the company evidence below, estimate the company's capacity.
Return JSON:
{{"people": {{"estimators": <int>, "bid_managers": <int>, "engineers": <int>, "project_managers": <int>, "specialist_engineers": <int>}},
  "equipment": [{{"name": "...", "total": <int>}}]}}
If a value is not implied by the documents, use a conservative small number. Do not invent specific staff.

COMPANY EVIDENCE:
{text}
"""
    try:
        d = await _ask(system, prompt)
    except Exception:
        return None
    return d if isinstance(d, dict) else None
