from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.modules.runtime_record import (
    GetRuntimeRecordQuery,
    RuntimeRecordPayload,
    RuntimeRecordStoragePort,
    UpsertRuntimeRecordCommand,
)
from src.modules.shared import EntityIdVO, ValidationError
from src.modules.shorter.domain.link.value_object import LinkIdVO
from src.modules.shorter.domain.template.entity import TemplateEntity
from src.modules.shorter.domain.template.repositories import TemplateRepositoryPort
from src.modules.shorter.domain.template.value_object import (
    TemplateEntityTypeVO,
    TemplateIdVO,
    TemplateTargetModuleTypeVO,
)


class RuntimeRecordTemplateRepository(TemplateRepositoryPort):
    OBJECT_NAME = "shorter_template"

    def __init__(
        self,
        *,
        tenant_id: EntityIdVO,
        runtime_record_storage: RuntimeRecordStoragePort,
    ):
        self._tenant_id = tenant_id
        self._runtime_record_storage = runtime_record_storage

    async def save(self, template: TemplateEntity) -> None:
        await self._runtime_record_storage.upsert_record(
            UpsertRuntimeRecordCommand(
                tenant_id=self._tenant_id.value,
                object_name_singular=self.OBJECT_NAME,
                record_id=template.id.value,
                values={
                    "created_at": template.created_at,
                    "updated_at": template.updated_at,
                    "created_by": template.created_by.value,
                    "default_code": template.default_code.value,
                    "target_module": template.target_module.value,
                    "target_entity": template.target_entity.value,
                    "target_entity_id": template.target_entity_id.value,
                },
            )
        )

    async def get_by_id(
        self,
        *,
        template_id: TemplateIdVO,
    ) -> TemplateEntity | None:
        payload = await self._runtime_record_storage.get_record(
            GetRuntimeRecordQuery(
                tenant_id=self._tenant_id.value,
                object_name_singular=self.OBJECT_NAME,
                record_id=template_id.value,
            )
        )
        if payload is None:
            return None
        return self._map_payload(payload)

    def _map_payload(self, payload: RuntimeRecordPayload) -> TemplateEntity:
        values = payload.system_values
        created_at = values.get("created_at")
        updated_at = values.get("updated_at")
        created_by = values.get("created_by")
        default_code = values.get("default_code")
        target_module = values.get("target_module")
        target_entity = values.get("target_entity")
        target_entity_id = values.get("target_entity_id")

        if created_by is None or default_code is None or target_entity_id is None:
            raise ValidationError(
                f"shorter_template '{payload.record_id}' has invalid required values"
            )
        if target_module is None or target_entity is None:
            raise ValidationError(
                f"shorter_template '{payload.record_id}' has invalid target values"
            )

        parsed_created_by = (
            created_by if isinstance(created_by, UUID) else UUID(str(created_by))
        )
        parsed_default_code = (
            default_code
            if isinstance(default_code, UUID)
            else UUID(str(default_code))
        )
        parsed_target_entity_id = (
            target_entity_id
            if isinstance(target_entity_id, UUID)
            else UUID(str(target_entity_id))
        )

        return TemplateEntity(
            id=TemplateIdVO.from_value(payload.record_id),
            created_at=self._coerce_datetime(
                value=created_at,
                context=f"shorter_template '{payload.record_id}' created_at",
            ),
            updated_at=self._coerce_datetime(
                value=updated_at,
                context=f"shorter_template '{payload.record_id}' updated_at",
            ),
            created_by=EntityIdVO.from_value(parsed_created_by),
            default_code=LinkIdVO.from_value(parsed_default_code),
            target_module=TemplateTargetModuleTypeVO(str(target_module).strip().lower()),
            target_entity=TemplateEntityTypeVO(str(target_entity).strip().lower()),
            target_entity_id=EntityIdVO.from_value(parsed_target_entity_id),
        )

    @staticmethod
    def _coerce_datetime(*, value: object, context: str) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError(f"{context} has invalid datetime value") from exc
        raise ValidationError(f"{context} has invalid datetime value")


__all__ = ["RuntimeRecordTemplateRepository"]
