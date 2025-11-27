# api/routers/admin.py
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from auth.deps import require_admin
from ingestion.ingest import ingest_file
from core.utils import logger as event_logger
from pathlib import Path
import uuid, shutil, asyncio

# DB helpers
import db.modules as modules_db
import db.logs as logs_db

# qdrant service (delete_by_module may be sync or async)
from core.services import qdrant_service

# config settings
from config.settings import settings

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

@router.post("/upload")
async def upload(file: UploadFile = File(...), module: str = Form(...), lang: str = Form("ja"), admin = Depends(require_admin)):
    """
    Upload a file and ingest it into the specified module.
    """
    docs_dir = Path("docs")
    module_dir = docs_dir / module
    module_dir.mkdir(parents=True, exist_ok=True)
    saved_path = module_dir / f"{uuid.uuid4().hex}_{file.filename}"
    # save file
    with saved_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    # ensure module db record exists
    existing = await modules_db.get_module_by_name(module)
    if not existing:
        await modules_db.create_module(module)
    # run ingestion (ingest_file should return metadata about upserted points)
    metadata = await ingest_file(module, saved_path, lang=lang)

    # log action
    await event_logger.log_action(admin["user_id"], "UPLOAD_INGEST", {"module": module, "file": str(saved_path), "meta": metadata})
    return {"ok": True, "meta": metadata}


@router.get("/modules")
async def list_modules(admin = Depends(require_admin)):
    """
    Return list of modules from DB.
    """
    mods = await modules_db.list_modules()
    # return a simple list for the SPA (it supports array of strings or objects)
    return {"modules": mods}


@router.get("/logs")
async def recent_logs(admin = Depends(require_admin), limit: int = 100):
    """
    Return recent logs (default limit 100).
    """
    rows = await logs_db.get_recent_logs(limit)
    # Convert rows to JSON-friendly dicts if rows are tuples
    parsed = []
    for r in rows:
        # r expected: (log_id, admin_id, action_type, details, timestamp)
        try:
            log_id, admin_id, action_type, details, timestamp = r
        except Exception:
            # If get_recent_logs already returns dicts, try pass-through
            parsed.append(r)
            continue
        parsed.append({
            "log_id": log_id,
            "admin_id": admin_id,
            "action_type": action_type,
            "details": details,
            "timestamp": timestamp
        })
    return {"logs": parsed}


@router.delete("/module/{module_name}")
async def delete_module(module_name: str, admin = Depends(require_admin)):
    """
    Delete a module:
      1) delete vectors from Qdrant collection for module (delete_by_module)
      2) delete docs folder
      3) delete DB record
      4) log action
    """
    # 0) ensure module exists
    module = await modules_db.get_module_by_name(module_name)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # 1) delete vectors from Qdrant
    try:
        res = qdrant_service.delete_by_module(settings.QDRANT_COLLECTION, module_name)
        if asyncio.iscoroutine(res):
            await res
    except Exception as exc:
        await event_logger.log_action(admin["user_id"], "DELETE_MODULE_FAILED_QDRANT", {"module": module_name, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Failed to delete vectors: {exc}")

    # 2) delete docs folder
    p = Path("docs") / module_name
    if p.exists():
        try:
            shutil.rmtree(p)
        except Exception as exc:
            await event_logger.log_action(admin["user_id"], "DELETE_MODULE_FAILED_FS", {"module": module_name, "error": str(exc)})
            raise HTTPException(status_code=500, detail=f"Failed to delete docs folder: {exc}")

    # 3) remove DB module record
    try:
        await modules_db.delete_module(module_name)
    except Exception as exc:
        await event_logger.log_action(admin["user_id"], "DELETE_MODULE_FAILED_DB", {"module": module_name, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Failed to remove module from DB: {exc}")

    # 4) log success
    await event_logger.log_action(admin["user_id"], "DELETE_MODULE", {"module": module_name})
    return {"ok": True, "module": module_name}
