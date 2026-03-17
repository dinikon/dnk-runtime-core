from __future__ import annotations

from src.modules.crm.application.commands import UpdateContactCommand
from src.modules.crm.application.dto import ContactDTO
from src.modules.crm.application.mappers import contact_to_dto
from src.modules.crm.domain.errors import ContactNotFoundError
from src.modules.crm.domain.repositories import ContactRepositoryProtocol
from src.modules.runtime_record.application import (
    RuntimeRecordApplicationService,
    WriteRuntimeValuesCommand,
)
from src.modules.shared.db.uow import UnitOfWorkProtocol


class UpdateContactUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        contact_repository: ContactRepositoryProtocol,
        runtime_record_service: RuntimeRecordApplicationService | None = None,
    ):
        self._uow = uow
        self._contact_repository = contact_repository
        self._runtime_record_service = runtime_record_service

    async def execute(self, command: UpdateContactCommand) -> ContactDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._update_within_transaction(command)
        return await self._update_within_transaction(command)

    async def _update_within_transaction(
        self,
        command: UpdateContactCommand,
    ) -> ContactDTO:
        contact = await self._contact_repository.get_by_id(command.contact_id)
        if contact is None:
            raise ContactNotFoundError(command.contact_id)

        updated_contact = contact.update(
            last_name=command.last_name,
            first_name=command.first_name,
            middle_name=command.middle_name,
        )
        await self._contact_repository.update(updated_contact)
        custom_fields = command.custom_fields or {}
        if custom_fields:
            tenant_id = _require_tenant_id(command.tenant_id)
            if self._runtime_record_service is None:
                raise RuntimeError("runtime_record_service is required for custom fields.")
            await self._runtime_record_service.write_values(
                WriteRuntimeValuesCommand(
                    tenant_id=tenant_id,
                    object_name_singular="contact",
                    record_id=updated_contact.id,
                    values=custom_fields,
                )
            )
        await self._uow.commit()

        return contact_to_dto(updated_contact, custom_fields=custom_fields)


def _require_tenant_id(tenant_id):
    if tenant_id is None:
        raise ValueError("tenant_id is required when custom fields are provided.")
    return tenant_id


__all__ = ["UpdateContactUseCase"]
