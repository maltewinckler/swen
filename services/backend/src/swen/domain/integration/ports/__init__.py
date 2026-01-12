"""Integration domain ports (interfaces).

Ports define the abstract interfaces for external integrations.
Implementations live in the infrastructure layer.
"""

from swen.domain.integration.ports.ai_model_registry import AIModelRegistry

__all__ = [
    "AIModelRegistry",
]

