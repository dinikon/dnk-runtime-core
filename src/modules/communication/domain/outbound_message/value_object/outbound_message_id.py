from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class OutboundMessageIdVO(EntityIdVO):
    """Communication outbound message id."""
