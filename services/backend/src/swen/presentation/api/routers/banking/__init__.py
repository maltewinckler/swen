from fastapi import APIRouter

from swen.presentation.api.routers.banking.bank_accounts import (
    router as _bank_accounts_router,
)
from swen.presentation.api.routers.banking.credentials import (
    router as _credentials_router,
)
from swen.presentation.api.routers.banking.discovery import router as _discovery_router

# Credentials CRUD + discovery (lookup, tan-methods, discover) share /bank-connections
bank_connections_router = APIRouter()
bank_connections_router.include_router(_credentials_router, prefix="/credentials")
bank_connections_router.include_router(_discovery_router)

# Bank accounts (imported into accounting domain) under /bank-accounts prefix
bank_accounts_router = _bank_accounts_router

__all__ = ["bank_connections_router", "bank_accounts_router"]
