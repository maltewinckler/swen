"""LRU cache for user data."""

from functools import lru_cache
from pathlib import Path
from uuid import UUID

from swen_ml.preprocessing.noise_model import NoiseModel
from swen_ml.storage.anchor_store import AnchorStore, get_anchor_path
from swen_ml.storage.example_store import ExampleStore, get_example_path
from swen_ml.storage.noise_store import get_noise_path, load_noise_model_or_empty


class UserDataCache:
    """Cache for user-specific ML data."""

    def __init__(self, data_dir: Path, max_users: int = 100):
        self._data_dir = data_dir
        self._max_users = max_users

        # Create cached loaders
        self._load_examples = lru_cache(maxsize=max_users)(self._load_examples_impl)
        self._load_anchors = lru_cache(maxsize=max_users)(self._load_anchors_impl)
        self._load_noise = lru_cache(maxsize=max_users)(self._load_noise_impl)

    def get_examples(self, user_id: UUID) -> ExampleStore:
        """Get user's example store (cached)."""
        return self._load_examples(user_id)

    def get_anchors(self, user_id: UUID) -> AnchorStore:
        """Get user's anchor store (cached)."""
        return self._load_anchors(user_id)

    def get_noise_model(self, user_id: UUID) -> NoiseModel:
        """Get user's noise model (cached)."""
        return self._load_noise(user_id)

    def invalidate(self, user_id: UUID) -> None:
        """Invalidate all caches for a user."""
        # Clear from LRU caches
        self._load_examples.cache_clear()
        self._load_anchors.cache_clear()
        self._load_noise.cache_clear()

    def _load_examples_impl(self, user_id: UUID) -> ExampleStore:
        path = get_example_path(self._data_dir, user_id)
        return ExampleStore.load_or_empty(path)

    def _load_anchors_impl(self, user_id: UUID) -> AnchorStore:
        path = get_anchor_path(self._data_dir, user_id)
        return AnchorStore.load_or_empty(path)

    def _load_noise_impl(self, user_id: UUID) -> NoiseModel:
        path = get_noise_path(self._data_dir, user_id)
        return load_noise_model_or_empty(path)

    @property
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "examples": self._load_examples.cache_info()._asdict(),
            "anchors": self._load_anchors.cache_info()._asdict(),
            "noise": self._load_noise.cache_info()._asdict(),
        }
