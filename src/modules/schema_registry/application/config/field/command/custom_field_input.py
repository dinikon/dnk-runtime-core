from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CustomFieldInput:
    """Входные данные для создания custom field metadata и колонки."""

    field_name: str
    type: str
    label: str
    description: str = ""
    is_nullable: bool = True
    default_value: str | None = None
    options: dict[str, str] = field(default_factory=dict)
    settings: dict[str, str] = field(default_factory=dict)


__all__ = ["CustomFieldInput"]
