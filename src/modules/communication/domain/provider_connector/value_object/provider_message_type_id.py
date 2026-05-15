from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ProviderMessageTypeIdVO(EntityIdVO):
    """Communication provider message type id."""
