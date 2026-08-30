"""Local semantic embeddings for evidence retrieval (fastembed / BAAI bge-small-en-v1.5, 384-dim).

No external key required. Falls back to keyword retrieval if the model is unavailable.
Every retrieved chunk keeps its source metadata (document/page) for traceability.
"""
import logging
import numpy as np

from rag.pipeline import retrieve as keyword_retrieve

logger = logging.getLogger("bidpilot.embeddings")

MODEL_NAME = "BAAI/bge-small-en-v1.5"
_model = None
_load_failed = False


def get_model():
    global _model, _load_failed
    if _model is not None or _load_failed:
        return _model
    try:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=MODEL_NAME, threads=1)
        logger.info("Embedding model loaded")
    except Exception as e:  # pragma: no cover
        _load_failed = True
        logger.error(f"Embedding model unavailable, falling back to keyword retrieval: {e}")
    return _model


def _embed(texts):
    model = get_model()
    if model is None:
        return None
    vecs = np.array(list(model.embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def attach_embeddings(chunks):
    """Precompute embeddings for a set of chunks once (in-place)."""
    texts = [c["text"] for c in chunks]
    if not texts:
        return chunks
    vecs = _embed(texts)
    if vecs is None:
        return chunks
    for c, v in zip(chunks, vecs):
        c["_emb"] = v
    return chunks


def semantic_retrieve(query, chunks, top_k=4):
    """Rank chunks by cosine similarity to the query. Keyword fallback on failure."""
    if not chunks:
        return []
    qv = _embed([query])
    if qv is None:
        return keyword_retrieve(query, chunks, top_k)
    q = qv[0]
    scored = []
    for c in chunks:
        emb = c.get("_emb")
        if emb is None:
            ev = _embed([c["text"]])
            if ev is None:
                return keyword_retrieve(query, chunks, top_k)
            emb = ev[0]
        score = float(np.dot(q, emb))
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for s, c in scored[:top_k]:
        item = {k: v for k, v in c.items() if k != "_emb"}
        item["retrieval_score"] = round(s, 4)
        out.append(item)
    return out
