from src.modules.crm.application.links.company_contacts import CompanyContactsService
from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.company.command import DeleteCompanyCommand
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class DeleteCompanyUseCase:
    """Физически удаляет tenant-scoped компанию."""

    def __init__(
        self,
        repository: CompanyRepositoryProtocol,
        contact_points: ContactPointsPort,
        links: CompanyContactsService,
    ):
        self.repository = repository
        self.links = links
        self.contact_points = contact_points

    async def __call__(self, command: DeleteCompanyCommand) -> None:
        """Удаляет запись либо поднимает CompanyNotFoundError."""
        expected = await self.links.queries.linked_contact_ids(
            command.tenant_id, command.company_id
        )
        contacts = await self.links.lock_contacts(
            command.tenant_id, requested=(), expected=expected
        )
        await self.repository.get(
            command.tenant_id, command.company_id, for_update=True
        )
        await self.links.apply(
            command.tenant_id,
            command.company_id,
            command.actor_id,
            requested=(),
            expected=expected,
            contacts=contacts,
        )
        await self.contact_points.remove(
            command.tenant_id,
            "crm.company",
            EntityIdVO.from_value(command.company_id.uuid),
        )
        await self.repository.delete(command.tenant_id, command.company_id)


__all__ = ["DeleteCompanyUseCase"]
