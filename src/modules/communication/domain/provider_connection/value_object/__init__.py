from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ProviderConnectionIdVO(EntityIdVO):
    """Communication provider connection id."""


__all__ = ["ProviderConnectionIdVO"]
