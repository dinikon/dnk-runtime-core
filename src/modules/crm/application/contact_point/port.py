from typing import Protocol

from src.modules.crm.application.contact_point.dto import (
    ContactPointDraftDTO,
    ContactPointsDTO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactPointsPort(Protocol):
    """Расширение CRM без зависимости Application от модуля ContactPoints."""

    async def list(
        self, tenant_id: EntityIdVO, owner_id: EntityIdVO
    ) -> ContactPointsDTO: ...

    async def sync(
        self,
        tenant_id: EntityIdVO,
        actor_id: EntityIdVO,
        owner_id: EntityIdVO,
        phones: tuple[ContactPointDraftDTO, ...] | None,
        emails: tuple[ContactPointDraftDTO, ...] | None,
    ) -> None: ...

    async def remove(self, tenant_id: EntityIdVO, owner_id: EntityIdVO) -> None: ...
