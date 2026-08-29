# RAG

## Ingestion
- `parse_pdf` (pypdf) extracts page-aware text and detects scanned PDFs (near-zero extractable text).
  Scanned files are flagged "Needs Review" — content is never invented (OCR not enabled in this build).
- `chunk_pages` splits each page into overlapping chunks, each retaining `{document_id, document_type, filename, page_number, section, text}`.

## Retrieval
- `retrieve` scores chunks against a query with a BM25-lite keyword measure (tf × idf over the chunk set).
- Tender evidence and company evidence are kept strictly separate (`document_type`).
- Top-k chunks feed the evidence matcher; the highest-scoring chunk becomes the cited source.

## Source attribution
Every requirement/finding carries `evidence_source_document` + `evidence_source_page`, surfaced in the
Evidence Viewer (extracted page text shown; no fabricated pixel highlights).

## Storage
PDF binaries live in Emergent object storage; extracted page text is stored in MongoDB `documents.pages`
(the source of truth for analysis and retrieval).
