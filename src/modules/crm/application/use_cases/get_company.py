from __future__ import annotations

from src.modules.crm.application.dto import CompanyDTO
from src.modules.crm.application.mappers import company_to_dto
from src.modules.crm.application.queries import GetCompanyQuery
from src.modules.crm.domain.errors import CompanyNotFoundError
from src.modules.crm.domain.repositories import CompanyRepositoryProtocol
from src.modules.runtime_record.application import (
    ReadRuntimeValuesQuery,
    RuntimeRecordApplicationService,
)


class GetCompanyUseCase:
    def __init__(
        self,
        *,
        company_repository: CompanyRepositoryProtocol,
        runtime_record_service: RuntimeRecordApplicationService | None = None,
    ):
        self._company_repository = company_repository
        self._runtime_record_service = runtime_record_service

    async def execute(self, query: GetCompanyQuery) -> CompanyDTO:
        company = await self._company_repository.get_by_id(query.company_id)
        if company is None:
            raise CompanyNotFoundError(query.company_id)
        custom_fields: dict[str, object | None] = {}
        if self._runtime_record_service is not None and query.tenant_id is not None:
            runtime_result = await self._runtime_record_service.read_values(
                ReadRuntimeValuesQuery(
                    tenant_id=query.tenant_id,
                    object_name_singular="company",
                    record_id=query.company_id,
                )
            )
            custom_fields = runtime_result.values
        return company_to_dto(company, custom_fields=custom_fields)


__all__ = ["GetCompanyUseCase"]
