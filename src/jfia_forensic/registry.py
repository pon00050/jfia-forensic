"""
DetectletRegistry — loads and indexes Detectlet YAML files.
"""

from __future__ import annotations

import yaml
from pathlib import Path
from pydantic import ValidationError

from .models import Detectlet


class DetectletRegistry:
    def __init__(self, detectlets: list[Detectlet]) -> None:
        self._detectlets = detectlets
        self._by_name: dict[str, Detectlet] = {d.name: d for d in detectlets}

    @classmethod
    def from_yaml_dir(cls, directory: str | Path) -> "DetectletRegistry":
        """Load all .yaml files from directory as Detectlet objects."""
        directory = Path(directory)
        detectlets: list[Detectlet] = []
        for yaml_path in sorted(directory.glob("*.yaml")):
            try:
                with open(yaml_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                detectlets.append(Detectlet.model_validate(data))
            except (yaml.YAMLError, ValidationError, KeyError) as e:
                raise ValueError(
                    f"Failed to load detectlet from {yaml_path.name}: {e}"
                ) from e
        return cls(detectlets)

    def get(self, name: str) -> Detectlet | None:
        """Return detectlet by exact name, or None if not found."""
        return self._by_name.get(name)

    def search(self, scheme: str | None = None) -> list[Detectlet]:
        """Return detectlets matching scheme. Returns all if scheme is None."""
        if scheme is None:
            return list(self._detectlets)
        return [d for d in self._detectlets if d.scheme == scheme]

    def all(self) -> list[Detectlet]:
        """Return all loaded detectlets."""
        return list(self._detectlets)
