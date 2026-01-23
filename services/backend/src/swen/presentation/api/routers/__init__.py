from swen.presentation.api.routers.accounts import router as accounts_router
from swen.presentation.api.routers.admin import router as admin_router
from swen.presentation.api.routers.analytics import router as analytics_router
from swen.presentation.api.routers.auth import router as auth_router
from swen.presentation.api.routers.credentials import router as credentials_router
from swen.presentation.api.routers.dashboard import router as dashboard_router
from swen.presentation.api.routers.exports import router as exports_router
from swen.presentation.api.routers.imports import router as imports_router
from swen.presentation.api.routers.mappings import router as mappings_router
from swen.presentation.api.routers.onboarding import router as onboarding_router
from swen.presentation.api.routers.preferences import router as preferences_router
from swen.presentation.api.routers.sync import router as sync_router
from swen.presentation.api.routers.transactions import router as transactions_router

__all__ = [
    "accounts_router",
    "admin_router",
    "analytics_router",
    "auth_router",
    "credentials_router",
    "dashboard_router",
    "exports_router",
    "imports_router",
    "mappings_router",
    "onboarding_router",
    "preferences_router",
    "sync_router",
    "transactions_router",
]
