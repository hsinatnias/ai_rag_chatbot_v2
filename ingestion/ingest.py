# ingestion/ingest.py
from pathlib import Path
from ingestion.chunker import chunk_text
from core.services.embedding_service import embed_text
from core.services.qdrant_service import upsert
import uuid, os, json

DOCS_DIR = Path("docs")

async def ingest_file(module: str, filepath: Path, lang: str = "ja"):
    # 1 - ensure module folder exists
    module_folder = DOCS_DIR / module
    module_folder.mkdir(parents=True, exist_ok=True)
    # 2 - read file (assume txt for example; pdf parser would extract text)
    text = filepath.read_text(encoding="utf-8")
    chunks = chunk_text(text)
    points = []
    for i, chunk in enumerate(chunks):
        vec = await embed_text(chunk)
        point_id = f"{filepath.stem}-{i}-{uuid.uuid4().hex[:8]}"
        payload = {"module": module, "file": filepath.name, "lang": lang, "text": chunk, "chunk_id": i}
        points.append({"id": point_id, "vector": vec, "payload": payload})
    # 3 - upsert in batches
    await upsert("kb_chunks", points)
    # return metadata
    return {"ingested_chunks": len(points), "file": filepath.name}
