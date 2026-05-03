from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.application.config.field.command import (
    CustomFieldInput,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateCustomObjectCommand:
    """Команда создания кастомного объекта."""

    tenant_id: EntityIdVO
    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str
    fields: tuple[CustomFieldInput, ...] = ()


__all__ = ["CreateCustomObjectCommand"]
