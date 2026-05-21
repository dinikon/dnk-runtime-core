from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.domain.contact_point.entity import ContactPointEntity
from src.modules.contact_point.domain.contact_point.value_object.contact_point_id import (
    ContactPointIdVO,
)
from src.modules.contact_point.domain.contact_point.value_object.contact_point_type import (
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


class ContactPointRepositoryProtocol(Protocol):
    async def load_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_point_id: ContactPointIdVO,
    ) -> ContactPointEntity | None: ...

    async def get_by_type_and_hash(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_point_type: ContactPointTypeVO,
        hash_value: str,
    ) -> ContactPointEntity | None: ...

    async def save_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_point: ContactPointEntity,
    ) -> ContactPointEntity: ...


__all__ = ["ContactPointRepositoryProtocol"]
