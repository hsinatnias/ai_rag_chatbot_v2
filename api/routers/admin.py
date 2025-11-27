# api/routers/admin.py
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Body, Query
from auth.deps import require_admin
from ingestion.ingest import ingest_file
from core.utils import logger as event_logger
from pathlib import Path
import uuid, shutil, asyncio
import os

# DB helpers
import db.modules as modules_db
import db.logs as logs_db

# qdrant service (delete_by_module may be sync or async)
from core.services import qdrant_service

# config settings
from config.settings import settings

# Router: keep endpoints protected, but use endpoint-level admin Depends to access admin info
router = APIRouter(prefix="/api/admin", tags=["admin"])

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
    try:
        # try with lang param, fall back if ingest_file signature differs
        try:
            metadata = await ingest_file(module, saved_path, lang=lang)
        except TypeError:
            metadata = await ingest_file(module, saved_path)
    except TypeError:
        # fallback for synchronous ingest_file
        try:
            metadata = ingest_file(module, saved_path, lang=lang)
        except TypeError:
            metadata = ingest_file(module, saved_path)
    # log action
    await event_logger.log_action(admin["user_id"], "UPLOAD_INGEST", {"module": module, "file": str(saved_path), "meta": metadata})
    return {"ok": True, "meta": metadata}


@router.get("/modules")
async def list_modules(admin = Depends(require_admin)):
    """
    Return list of modules from DB.
    """
    mods = await modules_db.list_modules()
    return {"modules": mods}


@router.get("/logs")
async def recent_logs(admin = Depends(require_admin), limit: int = 100):
    """
    Return recent logs (default limit 100).
    """
    rows = await logs_db.get_recent_logs(limit)
    parsed = []
    for r in rows:
        try:
            log_id, admin_id, action_type, details, timestamp = r
        except Exception:
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


# List files in a module
@router.get("/module/{module_name}/files")
async def list_module_files(module_name: str, admin = Depends(require_admin)):
    """
    Return list of files saved in docs/<module_name>.
    """
    docs_dir = Path("docs")
    module_dir = docs_dir / module_name
    if not module_dir.exists() or not module_dir.is_dir():
        raise HTTPException(status_code=404, detail="Module not found")
    files = []
    for p in sorted(module_dir.iterdir(), key=lambda x: x.name):
        if p.is_file():
            files.append({
                "name": p.name,
                "path": str(p),
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime
            })
    return {"files": files}


# Delete a single file inside a module
@router.delete("/module/{module_name}/file")
async def delete_module_file(module_name: str, name: str = Query(...), admin = Depends(require_admin)):
    """
    Delete a file under docs/<module_name>/<name>.
    Query param: ?name=<filename>
    """
    docs_dir = Path("docs")
    module_dir = docs_dir / module_name
    if not module_dir.exists() or not module_dir.is_dir():
        raise HTTPException(status_code=404, detail="Module not found")
    target = (module_dir / name).resolve()
    # prevent path traversal
    if not str(target).startswith(str(module_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        target.unlink()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {exc}")
    # log action using event_logger (fixed variable name)
    await event_logger.log_action(admin["user_id"], "DELETE_FILE", {"module": module_name, "file": name})
    return {"ok": True, "file": name}


# Re-ingest a saved file
@router.post("/module/{module_name}/file/reingest")
async def reingest_module_file(module_name: str, payload: dict = Body(...), admin = Depends(require_admin)):
    """
    Re-ingest a saved file present in docs/<module>/<filename>.
    Body: {"filename": "<name>", "lang": "ja"}  # lang optional
    """
    filename = payload.get("filename")
    lang = payload.get("lang", None)  # optional override
    if not filename:
        raise HTTPException(status_code=400, detail="filename required")

    docs_dir = Path("docs")
    module_dir = docs_dir / module_name
    if not module_dir.exists() or not module_dir.is_dir():
        raise HTTPException(status_code=404, detail="Module not found")

    target = (module_dir / filename).resolve()
    if not str(target).startswith(str(module_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # determine language: prefer provided lang, else keep 'ja' default
    use_lang = lang if lang else "ja"

    try:
        meta = await ingest_file(module_name, target, lang=use_lang)
    except Exception as exc:
        await event_logger.log_action(admin["user_id"], "REINGEST_FAILED", {"module": module_name, "file": filename, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"Reingest failed: {exc}")

    await event_logger.log_action(admin["user_id"], "REINGEST_FILE", {"module": module_name, "file": filename, "lang": use_lang})
    return {"ok": True, "meta": meta}

    return {"ok": True, "meta": meta}
