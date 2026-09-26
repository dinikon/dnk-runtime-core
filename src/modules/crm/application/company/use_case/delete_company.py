from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.company.command import DeleteCompanyCommand
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class DeleteCompanyUseCase:
    """Физически удаляет tenant-scoped компанию."""

    def __init__(
        self, repository: CompanyRepositoryProtocol, contact_points: ContactPointsPort
    ):
        self.repository = repository
        self.contact_points = contact_points

    async def __call__(self, command: DeleteCompanyCommand) -> None:
        """Удаляет запись либо поднимает CompanyNotFoundError."""
        await self.repository.get(
            command.tenant_id, command.company_id, for_update=True
        )
        await self.contact_points.remove(
            command.tenant_id,
            "crm.company",
            EntityIdVO.from_value(command.company_id.uuid),
        )
        await self.repository.delete(command.tenant_id, command.company_id)


__all__ = ["DeleteCompanyUseCase"]
