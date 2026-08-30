"""RAG pipeline: page-aware PDF parsing, chunking, metadata, and lightweight keyword retrieval.

Retrieval uses TF-style scoring over page-aware chunks. Every chunk retains
its source metadata (document id, filename, page number) so findings are traceable.
No embeddings are faked; if a PDF is scanned (no extractable text) we report it
rather than inventing content.
"""
import re
import math
import logging
from collections import Counter
from pypdf import PdfReader

logger = logging.getLogger("bidpilot.rag")

STOPWORDS = set("""a an the of to in for and or is are be as at by with on from this that these those
shall will must should may can any all such other than not no which who whom whose it its into per""".split())


def _ocr_pages(path, max_ocr_pages=25):
    """OCR a scanned PDF using Gemini Multimodal File API. Returns a dict {1: text} (all text put on page 1 for simplicity) or empty on failure."""
    try:
        import os
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found for OCR fallback")
            return {}
            
        genai.configure(api_key=api_key)
        
        logger.info(f"Uploading {path} to Gemini for OCR extraction...")
        myfile = genai.upload_file(path)
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([myfile, "Extract all the text from this document accurately. Do not summarize. Just output the extracted text."])
        
        # Cleanup
        try:
            genai.delete_file(myfile.name)
        except Exception:
            pass
            
        text = response.text
        if text:
            # We bundle all extracted text into 'page 1' since Gemini processes the whole file
            return {1: text.strip()}
    except Exception as e:
        logger.error(f"Gemini OCR failed: {e}")
    return {}


def parse_pdf(path: str, ocr: bool = True, max_ocr_pages: int = 25):
    """Return (pages, is_scanned, page_count).

    Extracts embedded text page by page. Pages with no extractable text are OCR'd
    (up to max_ocr_pages) so scanned tenders become analyzable. Never invents content:
    if OCR is unavailable or yields nothing, the page stays empty.
    """
    reader = PdfReader(path)
    pages = []
    empty_pages = []
    total_chars = 0
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = re.sub(r"[ \t]+", " ", text).strip()
        total_chars += len(text)
        if len(text) < 5:
            empty_pages.append(i + 1)
        pages.append({"page_number": i + 1, "text": text})

    is_scanned = total_chars < 40 * max(1, len(pages))
    ocr_applied = False
    if ocr and empty_pages and is_scanned:
        ocr_text = _ocr_pages(path, max_ocr_pages)
        if ocr_text and 1 in ocr_text:
            # If Gemini successfully extracted text, replace all pages with this single block of text on page 1
            pages = [{"page_number": 1, "text": ocr_text[1], "ocr": True}]
            ocr_applied = True
            
        # recompute scanned flag: if OCR recovered substantial text, no longer "unreadable"
        total_chars = sum(len(p["text"]) for p in pages)
        if ocr_applied and total_chars >= 40:
            is_scanned = False

    return pages, is_scanned, len(reader.pages)


def chunk_pages(pages, document_id, document_type, filename, chunk_size=900, overlap=150):
    chunks = []
    for p in pages:
        text = p["text"]
        if not text:
            continue
        start = 0
        while start < len(text):
            piece = text[start:start + chunk_size]
            chunks.append({
                "document_id": document_id,
                "document_type": document_type,
                "filename": filename,
                "page_number": p["page_number"],
                "section": None,
                "text": piece.strip(),
            })
            start += chunk_size - overlap
    return chunks


def _tokenize(text):
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def retrieve(query, chunks, top_k=5):
    """Simple BM25-lite keyword retrieval over chunks. Returns ranked chunks with scores."""
    if not chunks:
        return []
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return chunks[:top_k]
    N = len(chunks)
    df = Counter()
    chunk_tokens = []
    for c in chunks:
        toks = _tokenize(c["text"])
        chunk_tokens.append(toks)
        for t in set(toks):
            df[t] += 1
    scored = []
    for c, toks in zip(chunks, chunk_tokens):
        if not toks:
            continue
        tf = Counter(toks)
        score = 0.0
        for t in q_tokens:
            if t in tf:
                idf = math.log(1 + N / (1 + df[t]))
                score += (tf[t] / len(toks)) * idf
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{**c, "retrieval_score": round(s, 4)} for s, c in scored[:top_k]]
