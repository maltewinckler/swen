from swen.presentation.api.routers.accounting import (
    accounts_router as accounting_accounts_router,
)
from swen.presentation.api.routers.accounting import (
    init_router as accounting_init_router,
)
from swen.presentation.api.routers.admin import router as admin_router
from swen.presentation.api.routers.analytics import router as analytics_router
from swen.presentation.api.routers.auth import router as auth_router
from swen.presentation.api.routers.banking import (
    bank_accounts_router,
    bank_connections_router,
)
from swen.presentation.api.routers.dashboard import router as dashboard_router
from swen.presentation.api.routers.exports import router as exports_router
from swen.presentation.api.routers.imports import router as imports_router
from swen.presentation.api.routers.integration import router as integration_router
from swen.presentation.api.routers.mappings import router as mappings_router
from swen.presentation.api.routers.onboarding import router as onboarding_router
from swen.presentation.api.routers.preferences import router as preferences_router
from swen.presentation.api.routers.sync import router as sync_router
from swen.presentation.api.routers.transactions import router as transactions_router

__all__ = [
    "accounting_accounts_router",
    "accounting_init_router",
    "admin_router",
    "analytics_router",
    "auth_router",
    "bank_accounts_router",
    "bank_connections_router",
    "dashboard_router",
    "exports_router",
    "imports_router",
    "integration_router",
    "mappings_router",
    "onboarding_router",
    "preferences_router",
    "sync_router",
    "transactions_router",
]
