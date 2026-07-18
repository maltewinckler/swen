from fastapi import APIRouter

from swen.presentation.api.banking.routers.credentials import (
    router as _credentials_router,
)
from swen.presentation.api.banking.routers.discovery import router as _discovery_router

# Credentials CRUD + discovery (lookup, tan-methods, discover) share /bank-connections
bank_connections_router = APIRouter()
bank_connections_router.include_router(_credentials_router, prefix="/credentials")
bank_connections_router.include_router(_discovery_router)

__all__ = ["bank_connections_router"]
