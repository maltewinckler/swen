"""Persistence for user noise models."""

import json
from pathlib import Path
from uuid import UUID

from swen_ml.preprocessing.noise_model import NoiseModel


def save_noise_model(model: NoiseModel, path: Path) -> None:
    """Save noise model to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(model.to_dict(), f)


def load_noise_model(path: Path) -> NoiseModel:
    """Load noise model from disk."""
    with open(path) as f:
        data = json.load(f)
    return NoiseModel.from_dict(data)


def load_noise_model_or_empty(path: Path) -> NoiseModel:
    """Load noise model from disk or return empty model."""
    if path.exists():
        return load_noise_model(path)
    return NoiseModel()


def get_noise_path(data_dir: Path, user_id: UUID) -> Path:
    """Get path for user's noise model."""
    return data_dir / "users" / str(user_id) / "noise_model.json"
