"""API configuration adapter.

Bridges the centralized swen_config settings with the API layer.
"""

from functools import lru_cache

from swen_config.settings import Settings, get_settings


@lru_cache
def get_api_settings() -> Settings:
    """Get settings from centralized configuration.

    Returns the main application settings (flat structure).
    """
    return get_settings()
