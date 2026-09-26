from dataclasses import replace
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.contact.dto import ContactPageDTO
from src.modules.crm.application.contact.query import (
    ContactQueryRepositoryProtocol,
    ListContactsQuery,
)


class ListContactsUseCase:
    """Возвращает найденную страницу контактов."""

    def __init__(
        self,
        repository: ContactQueryRepositoryProtocol,
        contact_points: ContactPointsPort,
    ):
        self.repository = repository
        self.contact_points = contact_points

    async def __call__(self, query: ListContactsQuery) -> ContactPageDTO:
        """Передаёт типизированный запрос в query repository."""
        page = await self.repository.list(query)
        ids = tuple(EntityIdVO.from_value(item.id.uuid) for item in page.items)
        points = await self.contact_points.get_many(query.tenant_id, "crm.contact", ids)
        return replace(
            page,
            items=tuple(
                replace(
                    item,
                    phones=points[record_id].phones,
                    emails=points[record_id].emails,
                )
                for item, record_id in zip(page.items, ids)
            ),
        )


__all__ = ["ListContactsUseCase"]
