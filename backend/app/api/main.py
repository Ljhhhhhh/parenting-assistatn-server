from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils, children, growth_records, documents, chat, child_details
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(children.router, prefix="/children", tags=["children"])
api_router.include_router(growth_records.router, prefix="/growth-records", tags=["growth-records"])
api_router.include_router(child_details.router, prefix="/child-details", tags=["child-details"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
