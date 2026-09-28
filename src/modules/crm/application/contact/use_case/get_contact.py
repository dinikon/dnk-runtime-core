from dataclasses import replace
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.contact.dto import ContactDetailsDTO
from src.modules.crm.application.contact.query import GetContactQuery
from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError


class GetContactUseCase:
    """Возвращает один tenant-scoped контакт."""

    def __init__(
        self,
        repository: ContactQueryRepositoryProtocol,
        contact_points: ContactPointsPort,
    ):
        self.repository = repository
        self.contact_points = contact_points

    async def __call__(self, query: GetContactQuery) -> ContactDetailsDTO:
        """Читает проекцию карточки и обогащает её точками контакта."""
        details = await self.repository.get_details(query.tenant_id, query.contact_id)
        if details is None:
            raise ContactNotFoundError("Contact not found.")
        record_id = EntityIdVO.from_value(details.id.uuid)
        points = (
            await self.contact_points.get_many(
                query.tenant_id, "crm.contact", (record_id,)
            )
        )[record_id]
        return replace(details, phones=points.phones, emails=points.emails)


__all__ = ["GetContactUseCase"]
