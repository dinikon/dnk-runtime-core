from src.modules.crm.application.contact_point.dto import ContactPointsDTO
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.application.company.command.sync_contact_points.command import (
    SyncCompanyContactPointsCommand,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class SyncCompanyContactPointsHandler:
    """Блокирует владельца и изменяет расширение в его UoW."""

    def __init__(
        self, repository: CompanyRepositoryProtocol, points: ContactPointsPort
    ) -> None:
        self._repository = repository
        self._points = points

    async def execute(
        self, command: SyncCompanyContactPointsCommand
    ) -> ContactPointsDTO:
        if await self._repository.get_for_update(command.company_id) is None:
            raise CompanyNotFoundError("Company not found.")
        await self._points.sync(
            command.tenant_id,
            command.actor_id,
            command.company_id,
            command.phones,
            command.emails,
        )
        return await self._points.list(command.tenant_id, command.company_id)
