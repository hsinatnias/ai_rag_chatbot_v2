# ingestion/ingest.py
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
import math
import re

from core.services.qdrant_service import upsert as upsert_points
from core.services.embedder import embed_texts
from config.settings import settings

# -----------------------
# Text extraction helpers
# -----------------------
def extract_text_from_file(filepath: Path) -> str:
    """
    Extract text from supported files.
    - .txt : raw read
    - .pdf : pypdf PdfReader
    Returns empty string if unsupported or extraction fails.
    """
    try:
        suffix = filepath.suffix.lower()
        if suffix == ".txt":
            return filepath.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except Exception:
                # pypdf not installed or failed import
                return ""
            try:
                reader = PdfReader(str(filepath))
                out = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        out.append(text)
                return "\n".join(out)
            except Exception:
                return ""
    except Exception:
        return ""
    return ""

# -----------------------
# Chunking helper
# -----------------------
def chunk_text(text: str, max_words: int = 250, overlap: int = 50) -> List[str]:
    """
    Simple chunker (word-based). Returns list of chunks where each chunk is ~max_words words,
    overlapping by `overlap`. This approximates token-based chunking without extra deps.
    Tweak max_words to control chunk size (200-400 words is a reasonable default).
    """
    if not text:
        return []

    # Normalize whitespace and split into words
    cleaned = re.sub(r'\s+', ' ', text).strip()
    words = cleaned.split(' ')
    if len(words) <= max_words:
        return [" ".join(words).strip()]

    chunks = []
    i = 0
    length = len(words)
    while i < length:
        chunk_words = words[i:i + max_words]
        chunks.append(" ".join(chunk_words).strip())
        # advance by max_words - overlap
        if i + max_words >= length:
            break
        i += (max_words - overlap)
    return chunks

# -----------------------
# Ingest function
# -----------------------
async def ingest_file(module: str, filepath: Path, lang: str = "ja") -> Dict[str, Any]:
    """
    Ingest a file into Qdrant (collection from settings).
    Returns metadata dict for admin UI.
    """
    # 1) extract text
    text = extract_text_from_file(filepath)
    if not text:
        return {"ok": False, "reason": "no_text_extracted", "module": module, "filename": filepath.name}

    # 2) chunk text
    # Choose chunk size sensible for your model; 250 words ~ ~200 tokens depending on language.
    chunks = chunk_text(text, max_words=250, overlap=50)
    if not chunks:
        return {"ok": False, "reason": "no_chunks", "module": module, "filename": filepath.name}

    # 3) embed chunks (async wrapper around sentence-transformers)
    vectors = await embed_texts(chunks)  # List[List[float]]

    # 4) assemble points
    points = []
    for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
        point_id = str(uuid.uuid4())
        payload = {
            "module": module,
            "filename": filepath.name,
            "source_path": str(filepath),
            "lang": lang,
            "chunk_index": idx,
            "text": chunk
        }
        points.append({
            "id": point_id,
            "vector": vec,
            "payload": payload
        })

    # 5) upsert into Qdrant — run in thread because qdrant client is blocking
    try:
        await asyncio.to_thread(upsert_points, settings.QDRANT_COLLECTION, points)
    except Exception as exc:
        return {"ok": False, "reason": f"qdrant_upsert_failed: {exc}", "module": module, "filename": filepath.name}

    # 6) return metadata
    return {
        "ok": True,
        "chunks": len(chunks),
        "module": module,
        "filename": filepath.name,
        "lang": lang
    }
