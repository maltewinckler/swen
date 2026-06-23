from fastapi import APIRouter

from swen.presentation.api.integration.routers.bank_account_setup import (
    router as _setup_router,
)
from swen.presentation.api.integration.routers.reconciliation import (
    router as _reconciliation_router,
)

router = APIRouter()
router.include_router(_setup_router, prefix="/setup")
router.include_router(_reconciliation_router, prefix="/reconciliation")

__all__ = ["router"]
