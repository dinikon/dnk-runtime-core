from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.application.dto import OwnerContactPointDTO
from src.modules.contact_point.application.selection.command import (
    ContactPointSelectionCommand,
)
from src.modules.contact_point.application.selection.dto import (
    ContactPointSelectionDTO,
    ContactPointSelectionListDTO,
)
from src.modules.contact_point.domain.binding import OwnerContactPointBinding
from src.modules.contact_point.domain.contact_point import (
    ContactPointIdVO,
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


class ContactPointSelectionRepositoryProtocol(Protocol):
    async def find_active_primary_owner_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
    ) -> OwnerContactPointDTO | None: ...

    async def find_last_active_owner_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
    ) -> OwnerContactPointDTO | None: ...

    async def list_active_owner_contact_points(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_type: ContactPointTypeVO,
    ) -> tuple[OwnerContactPointDTO, ...]: ...

    async def find_active_owner_contact_point(
        self,
        *,
        tenant_id: EntityIdVO,
        owner: OwnerContactPointBinding,
        contact_point_id: ContactPointIdVO,
    ) -> OwnerContactPointDTO | None: ...


class ContactPointSelectionPort(Protocol):
    async def select_one(
        self,
        command: ContactPointSelectionCommand,
    ) -> ContactPointSelectionDTO: ...

    async def select_many(
        self,
        command: ContactPointSelectionCommand,
    ) -> ContactPointSelectionListDTO: ...


__all__ = [
    "ContactPointSelectionPort",
    "ContactPointSelectionRepositoryProtocol",
]
