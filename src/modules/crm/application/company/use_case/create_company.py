from typing import Protocol

from src.modules.crm.application.company.command import CreateCompanyCommand
from src.modules.crm.application.company.dto import CompanyDTO
from src.modules.crm.domain.company.entity import CompanyEntity
from src.modules.crm.domain.company.repository import CompanyCommandRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class CreateCompanyUseCaseProtocol(Protocol):
    """Порт use case создания компании."""

    async def __call__(self, command: CreateCompanyCommand) -> CompanyDTO:
        """Создает компанию и возвращает DTO."""
        ...


class CreateCompanyUseCase:
    """Use case создания CRM-компании."""

    def __init__(
        self,
        *,
        command_repository: CompanyCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует use case командным репозиторием и clock-портом."""
        self._command_repository = command_repository
        self._clock = clock

    async def __call__(self, command: CreateCompanyCommand) -> CompanyDTO:
        """Выполняет команду создания компании и мапит entity в DTO."""
        now = self._clock.now()
        company = CompanyEntity.create(
            id_=command.company_id,
            now=now,
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
