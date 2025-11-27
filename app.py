from fastapi import FastAPI
from config.settings import settings


app = FastAPI(title="RAG Chatbot")


# import routers lazily to avoid circular imports
from api.routers.chat import router as chat_router
from api.routers.auth import router as auth_router


app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"ok": True}