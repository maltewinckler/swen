from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swen_ml.config.settings import Settings
    from swen_ml.inference._models import Encoder
    from swen_ml.inference.classification.enrichment.service import EnrichmentService


@dataclass
class SharedInfrastructure:
    """Heavy resources shared across all requests."""

    encoder: Encoder
    settings: Settings
    enrichment_service: EnrichmentService | None = None

    @classmethod
    def create(
        cls,
        encoder: Encoder,
        settings: Settings,
        enrichment_service: EnrichmentService | None = None,
    ) -> SharedInfrastructure:
        """Create shared infrastructure from settings."""
        return cls(
            encoder=encoder,
            settings=settings,
            enrichment_service=enrichment_service,
        )
