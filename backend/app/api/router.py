"""Central API router."""
from fastapi import APIRouter
from app.api.routes import auth, conversations, itsm, users, admin, webhook

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(itsm.router, prefix="/itsm", tags=["itsm"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
