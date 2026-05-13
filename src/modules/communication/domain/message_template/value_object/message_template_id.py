from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class MessageTemplateIdVO(EntityIdVO):
    """Communication message template id."""
