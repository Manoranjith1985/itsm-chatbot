import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.config import settings
from app.db.init_db import init_db
from app.api.routes import auth, chat, tickets, settings as settings_router
from app.api.routes import admin, docs

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
INDEX_HTML = os.path.join(STATIC_DIR, "index.html")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="ITSM-PMO AI Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── API routes ─────────────────────────────────────────────────────────────
app.include_router(auth.router,            prefix="/api/v1/auth",     tags=["auth"])
app.include_router(chat.router,            prefix="/api/v1",          tags=["chat"])
app.include_router(tickets.router,         prefix="/api/v1/tickets",  tags=["tickets"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(admin.router,           prefix="/api/v1/admin",    tags=["admin"])
app.include_router(docs.router,            prefix="/api/v1/docs",     tags=["docs"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse(INDEX_HTML)
