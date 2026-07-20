from fastapi import APIRouter

from swen.presentation.api.banking.routers.bank_account_setup import (
    router as _setup_router,
)
from swen.presentation.api.integration.routers.bank_accounts import (
    router as bank_accounts_router,
)
from swen.presentation.api.integration.routers.reconciliation import (
    router as _reconciliation_router,
)

# bank_account_setup is a banking-domain router (imports only banking commands/schemas)
# but stays exposed under /integration/setup, the product surface the frontend calls.
router = APIRouter()
router.include_router(_setup_router, prefix="/setup")
router.include_router(_reconciliation_router, prefix="/reconciliation")

# Bank accounts (accounting domain data) kept as its own top-level router --
# it's registered separately under /bank-accounts, not nested under /integration.
__all__ = ["router", "bank_accounts_router"]
