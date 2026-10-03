from src.modules.crm.application.company.command.create_company.command import (
    CreateCompanyCommand,
)
from src.modules.crm.application.company.command.create_company.dto import (
    CreateCompanyResultDTO,
)
from src.modules.crm.domain.company.aggregate import CompanyEntity
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class CreateCompanyHandler:
    def __init__(
        self,
        repository: CompanyRepositoryProtocol,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._uuid_generator = uuid_generator

    async def execute(self, command: CreateCompanyCommand) -> CreateCompanyResultDTO:
        company = CompanyEntity.create(
            company_id=CompanyIdVO.from_value(self._uuid_generator.new()),
            legal_name=command.legal_name,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(company)
        return CreateCompanyResultDTO(
            id=company.id.uuid,
            legal_name=company.legal_name.value,
            created_at=company.created_at,
            updated_at=company.updated_at,
            created_by=company.created_by.uuid,
            updated_by=company.updated_by.uuid,
        )
