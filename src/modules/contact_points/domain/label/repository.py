from typing import Protocol
from src.modules.contact_points.domain.label.entity import ContactPointLabel
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactPointLabelRepositoryProtocol(Protocol):
    """Tenant-scoped хранение подписей; блокировки согласуют archive и bind."""

    async def get(
        self,
        tenant_id: EntityIdVO,
        label_id: ContactPointLabelIdVO,
        *,
        for_update: bool = False,
    ) -> ContactPointLabel: ...
    async def list(
        self,
        tenant_id: EntityIdVO,
        point_type: ContactPointType | None = None,
        *,
        for_share: bool = False,
    ) -> tuple[ContactPointLabel, ...]: ...
    async def add(self, tenant_id: EntityIdVO, label: ContactPointLabel) -> None: ...
    async def save(self, tenant_id: EntityIdVO, label: ContactPointLabel) -> None: ...


__all__ = ["ContactPointLabelRepositoryProtocol"]
