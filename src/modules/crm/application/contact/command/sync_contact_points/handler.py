from src.modules.crm.application.contact_point.dto import ContactPointsDTO
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.application.contact.command.sync_contact_points.command import (
    SyncContactContactPointsCommand,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol


class SyncContactContactPointsHandler:
    """Блокирует владельца и изменяет расширение в его UoW."""

    def __init__(
        self, repository: ContactRepositoryProtocol, points: ContactPointsPort
    ) -> None:
        self._repository = repository
        self._points = points

    async def execute(
        self, command: SyncContactContactPointsCommand
    ) -> ContactPointsDTO:
        if await self._repository.get_for_update(command.contact_id) is None:
            raise ContactNotFoundError("Contact not found.")
        await self._points.sync(
            command.tenant_id,
            command.actor_id,
            command.contact_id,
            command.phones,
            command.emails,
        )
        return await self._points.list(command.tenant_id, command.contact_id)
