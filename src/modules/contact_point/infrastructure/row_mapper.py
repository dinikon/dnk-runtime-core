from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.contact_point.domain.binding import (
    ContactPointBindingEntity,
    ContactPointBindingIdVO,
    OwnerContactPointBinding,
)
from src.modules.contact_point.domain.contact_point import (
    ContactPointEntity,
    ContactPointIdVO,
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


def contact_point_entity(row: Mapping[str, Any]) -> ContactPointEntity:
    return ContactPointEntity(
        id=ContactPointIdVO.from_value(as_uuid(row.get("id"))),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
        contact_point_type=ContactPointTypeVO(as_str(row.get("contact_point_type"))),
        raw_value=as_str(row.get("raw_value")),
        display_value=as_str(row.get("display_value")),
        normalized_value=as_str(row.get("normalized_value")),
        hash_value=as_str(row.get("normalized_hash")),
    )


def contact_point_binding_entity(row: Mapping[str, Any]) -> ContactPointBindingEntity:
    return ContactPointBindingEntity(
        id=ContactPointBindingIdVO.from_value(as_uuid(row.get("id"))),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
        contact_point_id=ContactPointIdVO.from_value(
            as_uuid(row.get("contact_point_id"))
        ),
        contact_point_type=ContactPointTypeVO(as_str(row.get("contact_point_type"))),
        owner=OwnerContactPointBinding(
            owner_object_id=EntityIdVO.from_value(as_uuid(row.get("owner_object_id"))),
            owner_record_id=EntityIdVO.from_value(as_uuid(row.get("owner_record_id"))),
        ),
        is_primary=as_bool(row.get("is_primary")),
        detached_at=as_optional_datetime(row.get("detached_at")),
        is_active=as_bool(row.get("is_active")),
    )


def as_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError("Runtime row must contain UUID value.")


def as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError("Runtime row must contain datetime value.")


def as_optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return as_datetime(value)


def as_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("Runtime row must contain string value.")


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError("Runtime row must contain bool value.")


__all__ = [
    "as_bool",
    "as_datetime",
    "as_optional_datetime",
    "as_str",
    "as_uuid",
    "contact_point_binding_entity",
    "contact_point_entity",
]
