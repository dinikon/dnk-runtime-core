from dataclasses import replace
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.contact.dto import ContactDTO, contact_dto
from src.modules.crm.application.contact.query import GetContactQuery
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol


class GetContactUseCase:
    """Возвращает один tenant-scoped контакт."""

    def __init__(
        self, repository: ContactRepositoryProtocol, contact_points: ContactPointsPort
    ):
        self.repository = repository
        self.contact_points = contact_points

    async def __call__(self, query: GetContactQuery) -> ContactDTO:
        """Читает aggregate и преобразует его в DTO."""
        entity = await self.repository.get(query.tenant_id, query.contact_id)
        record_id = EntityIdVO.from_value(entity.id.uuid)
        points = (
            await self.contact_points.get_many(
                query.tenant_id, "crm.contact", (record_id,)
            )
        )[record_id]
        return replace(contact_dto(entity), phones=points.phones, emails=points.emails)


__all__ = ["GetContactUseCase"]
