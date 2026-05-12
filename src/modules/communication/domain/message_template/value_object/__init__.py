from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class MessageTemplateIdVO(EntityIdVO):
    """Communication message template id."""


@dataclass(frozen=True, slots=True)
class TemplateVersionIdVO(EntityIdVO):
    """Communication template version id."""


__all__ = [
    "MessageTemplateIdVO",
    "TemplateVersionIdVO",
]
