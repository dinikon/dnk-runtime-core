from src.modules.crm.application.contact.dto import ContactDTO, contact_dto
from src.modules.crm.application.contact.query import GetContactQuery
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol


class GetContactUseCase:
    """Возвращает один tenant-scoped контакт."""

    def __init__(self, repository: ContactRepositoryProtocol):
        self.repository = repository

    async def __call__(self, query: GetContactQuery) -> ContactDTO:
        """Читает aggregate и преобразует его в DTO."""
        return contact_dto(await self.repository.get(query.tenant_id, query.contact_id))


__all__ = ["GetContactUseCase"]
