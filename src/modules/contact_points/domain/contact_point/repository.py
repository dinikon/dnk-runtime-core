from typing import Protocol
from src.modules.contact_points.domain.contact_point.entity import ContactPoint
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
    ContactPointValueVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactPointRepositoryProtocol(Protocol):
    """Tenant-scoped хранение канонических адресов."""

    async def get(
        self, tenant_id: EntityIdVO, point_id: ContactPointIdVO
    ) -> ContactPoint: ...
    async def find_by_canonical(
        self,
        tenant_id: EntityIdVO,
        point_type: ContactPointType,
        value: ContactPointValueVO,
    ) -> ContactPoint | None: ...
    async def get_or_create(
        self, tenant_id: EntityIdVO, candidate: ContactPoint
    ) -> ContactPoint: ...


__all__ = ["ContactPointRepositoryProtocol"]
