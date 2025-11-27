# api/routers/admin.py (skeleton)
from fastapi import APIRouter, UploadFile, File, Form, Depends
from auth.deps import require_admin
from ingestion.ingest import ingest_file
from core.utils import logger as logger
from pathlib import Path
import uuid, shutil

router = APIRouter(prefix="/api/admin")

@router.post("/upload")
async def upload(file: UploadFile = File(...), module: str = Form(...), lang: str = Form("ja"), admin = Depends(require_admin)):
    docs_dir = Path("docs")
    module_dir = docs_dir / module
    module_dir.mkdir(parents=True, exist_ok=True)
    saved_path = module_dir / f"{uuid.uuid4().hex}_{file.filename}"
    with saved_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    metadata = await ingest_file(module, saved_path, lang=lang)
    # log action (we'll implement logger)
    return {"ok": True, "meta": metadata}


@router.delete("/module/{module_name}")
async def delete_module(module_name: str, admin = Depends(require_admin)):
    # 1 - delete vectors
    from core.services.qdrant_service import delete_by_module
    delete_by_module(settings.QDRANT_COLLECTION, module_name)

    # 2 - delete docs folder
    import shutil, os
    p = Path("docs") / module_name
    if p.exists():
        shutil.rmtree(p)

    # 3 - remove DB module record (implement db/modules.py)
    await db.modules.delete_module(module_name)

    # 4 - log
    await logger.log_action(admin["user_id"], "DELETE_MODULE", {"module": module_name})
    return {"ok": True}

