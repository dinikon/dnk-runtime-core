from typing import Protocol

from src.modules.crm.application.company.command import UpdateCompanyCommand
from src.modules.crm.application.company.dto import CompanyDTO
from src.modules.crm.domain.company.entity import CompanyEntity
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.repository import CompanyCommandRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class UpdateCompanyUseCaseProtocol(Protocol):
    """Порт use case обновления компании."""

    async def __call__(self, command: UpdateCompanyCommand) -> CompanyDTO:
        """Обновляет компанию и возвращает DTO."""
        ...


class UpdateCompanyUseCase:
    """Use case обновления CRM-компании."""

    def __init__(
        self,
        *,
        command_repository: CompanyCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует use case командным репозиторием и clock-портом."""
        self._command_repository = command_repository
        self._clock = clock

    async def __call__(self, command: UpdateCompanyCommand) -> CompanyDTO:
        """Выполняет команду обновления компании и мапит entity в DTO."""
        company = await self._command_repository.load(
            tenant_id=command.tenant_id,
            company_id=command.company_id,
        )
        if company is None:
            raise CompanyNotFoundError(str(command.company_id))

        company.update(
            now=self._clock.now(),
            legal_name=command.legal_name,
        )
        company = await self._command_repository.save(
            tenant_id=command.tenant_id,
            company=company,
        )
        return self._to_dto(company)

    @staticmethod
    def _to_dto(company: CompanyEntity) -> CompanyDTO:
        """Мапит CompanyEntity в CompanyDTO."""
        return CompanyDTO(
            id=company.id.uuid,
            created_at=company.created_at,
            updated_at=company.updated_at,
            legal_name=company.legal_name.value,
        )
