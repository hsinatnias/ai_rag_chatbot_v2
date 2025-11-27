from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from config.settings import settings


app = FastAPI(title="RAG Chatbot")



# import routers lazily to avoid circular imports
from api.routers.chat import router as chat_router
from api.routers.auth import router as auth_router
from api.routers.admin import router as admin_router


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)


#Serves Single Page Application from ./public (index.html served at /)
app.mount("/",StaticFiles(directory="public", html=True), name="public")

@app.middleware("http")
async def disable_html_caching(request: Request, call_next):
    resp = await call_next(request)
    content_type = resp.headers.get("content-type", "")
    # disable caching for HTML pages (index.html / SPA)
    if content_type.startswith("text/html"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
    return resp


@app.get("/health")
def health():
    return {"ok": True}