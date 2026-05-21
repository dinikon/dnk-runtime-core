from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.domain.binding.entity import ContactPointBindingEntity
from src.modules.contact_point.domain.binding.value_object.contact_point_binding_id import (
    ContactPointBindingIdVO,
)
from src.modules.contact_point.domain.binding.value_object.owner_binding import (
    OwnerContactPointBinding,
)
from src.modules.contact_point.domain.contact_point.value_object.contact_point_id import (
    ContactPointIdVO,
)
from src.modules.contact_point.domain.contact_point.value_object.contact_point_type import (
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


class ContactPointBindingRepositoryProtocol(Protocol):
    async def load_binding(
        self,
        *,
        tenant_id: EntityIdVO,
        binding_id: ContactPointBindingIdVO,
    ) -> ContactPointBindingEntity | None: ...

    async def find_by_owner_and_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_id: ContactPointIdVO,
    ) -> ContactPointBindingEntity | None: ...

    async def find_first_active_by_owner_and_type(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
    ) -> ContactPointBindingEntity | None: ...

    async def find_active_primary_by_owner_and_type(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
    ) -> ContactPointBindingEntity | None: ...

    async def unset_primary_for_owner_and_type(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
        exclude_binding_id: ContactPointBindingIdVO | None = None,
    ) -> None: ...

    async def has_active_bindings_for_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_point_id: ContactPointIdVO,
    ) -> bool: ...

    async def save_binding(
        self,
        *,
        tenant_id: EntityIdVO,
        binding: ContactPointBindingEntity,
    ) -> ContactPointBindingEntity: ...


__all__ = ["ContactPointBindingRepositoryProtocol"]
