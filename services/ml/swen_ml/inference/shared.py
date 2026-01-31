from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swen_ml.config.settings import Settings
    from swen_ml.inference._models import Encoder
    from swen_ml.inference.classification.enrichment import KeywordPort, SearXNGAdapter


@dataclass
class SharedInfrastructure:
    """Heavy resources shared across all requests."""

    encoder: Encoder
    settings: Settings
    keyword_adapter: KeywordPort | None = None
    searxng_adapter: SearXNGAdapter | None = None
