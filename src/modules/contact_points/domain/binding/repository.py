from dataclasses import dataclass
from typing import Protocol
from src.modules.contact_points.domain.binding.entity import ContactPointBinding
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.contact_point.entity import ContactPoint
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class BoundContactPoint:
    """Связь с каноническим значением для пакетного чтения."""

    binding: ContactPointBinding
    point: ContactPoint


class ContactPointBindingRepositoryProtocol(Protocol):
    """Хранение связей; владелец должен блокировать target перед записью."""

    async def list_for_targets(
        self, tenant_id: EntityIdVO, targets: tuple[ContactPointTargetVO, ...]
    ) -> tuple[BoundContactPoint, ...]: ...
    async def list_targets(
        self, tenant_id: EntityIdVO, point_id: ContactPointIdVO
    ) -> tuple[ContactPointTargetVO, ...]: ...
    async def replace_for_target(
        self,
        tenant_id: EntityIdVO,
        target: ContactPointTargetVO,
        bindings: tuple[ContactPointBinding, ...],
    ) -> None: ...
    async def remove_target(
        self, tenant_id: EntityIdVO, target: ContactPointTargetVO
    ) -> None: ...


__all__ = ["BoundContactPoint", "ContactPointBindingRepositoryProtocol"]
