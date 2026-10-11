from dataclasses import fields, is_dataclass
from typing import Any
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def transport_value(value: Any) -> Any:
    """Сериализует вложенные DTO и VO идентичностей в стабильные HTTP значения."""
    if isinstance(value, EntityIdVO):
        return value.uuid
    if is_dataclass(value):
        return {f.name: transport_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {k: transport_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(transport_value(v) for v in value)
    return value
