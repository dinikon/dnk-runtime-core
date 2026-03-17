from __future__ import annotations

from src.modules.crm.application.commands import UpdateCompanyCommand
from src.modules.crm.application.dto import CompanyDTO
from src.modules.crm.application.mappers import company_to_dto
from src.modules.crm.domain.errors import CompanyNotFoundError
from src.modules.crm.domain.repositories import CompanyRepositoryProtocol
from src.modules.runtime_record.application import (
    RuntimeRecordApplicationService,
    WriteRuntimeValuesCommand,
)
from src.modules.shared.db.uow import UnitOfWorkProtocol


class UpdateCompanyUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        company_repository: CompanyRepositoryProtocol,
        runtime_record_service: RuntimeRecordApplicationService | None = None,
    ):
        self._uow = uow
        self._company_repository = company_repository
        self._runtime_record_service = runtime_record_service

    async def execute(self, command: UpdateCompanyCommand) -> CompanyDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._update_within_transaction(command)
        return await self._update_within_transaction(command)

    async def _update_within_transaction(
        self,
        command: UpdateCompanyCommand,
    ) -> CompanyDTO:
        company = await self._company_repository.get_by_id(command.company_id)
        if company is None:
            raise CompanyNotFoundError(command.company_id)

        updated_company = company.update(
            last_name=command.last_name,
            company_name=command.company_name,
        )
        await self._company_repository.update(updated_company)
        custom_fields = command.custom_fields or {}
        if custom_fields:
            tenant_id = _require_tenant_id(command.tenant_id)
            if self._runtime_record_service is None:
                raise RuntimeError("runtime_record_service is required for custom fields.")
            await self._runtime_record_service.write_values(
                WriteRuntimeValuesCommand(
                    tenant_id=tenant_id,
                    object_name_singular="company",
                    record_id=updated_company.id,
                    values=custom_fields,
                )
            )
        await self._uow.commit()

        return company_to_dto(updated_company, custom_fields=custom_fields)


def _require_tenant_id(tenant_id):
    if tenant_id is None:
        raise ValueError("tenant_id is required when custom fields are provided.")
    return tenant_id


__all__ = ["UpdateCompanyUseCase"]
