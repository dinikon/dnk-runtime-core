from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.modules.runtime_record import (
    FindRuntimeRecordQuery,
    GetRuntimeRecordQuery,
    RuntimeRecordPayload,
    RuntimeRecordStoragePort,
    UpsertRuntimeRecordCommand,
)
from src.modules.shared import EntityIdVO, ValidationError
from src.modules.shorter.domain.link.entity import LinkEntity
from src.modules.shorter.domain.link.repositories import LinkRepositoryPort
from src.modules.shorter.domain.link.value_object import LinkIdVO
from src.modules.shorter.domain.shared.ports import LinkCodeUniquenessCheckerPort


class RuntimeRecordLinkRepository(
    LinkRepositoryPort,
    LinkCodeUniquenessCheckerPort,
):
    OBJECT_NAME = "shorter_link"

    def __init__(self, runtime_record_storage: RuntimeRecordStoragePort):
        self._runtime_record_storage = runtime_record_storage

    async def save(self, link: LinkEntity) -> None:
        await self._runtime_record_storage.upsert_record(
            UpsertRuntimeRecordCommand(
                tenant_id=link.domain_id.value,
                object_name_singular=self.OBJECT_NAME,
                record_id=link.id.value,
                values={
                    "created_at": link.created_at,
                    "domain_id": link.domain_id.value,
                    "code": link.code,
                },
            )
        )

    async def get_by_id(
        self,
        *,
        domain_id: EntityIdVO,
        link_id: LinkIdVO,
    ) -> LinkEntity | None:
        payload = await self._runtime_record_storage.get_record(
            GetRuntimeRecordQuery(
                tenant_id=domain_id.value,
                object_name_singular=self.OBJECT_NAME,
                record_id=link_id.value,
            )
        )
        if payload is None:
            return None
        return self._map_payload(payload)

    async def exists_by_domain_and_code(
        self,
        *,
        domain_id: EntityIdVO,
        code: str,
    ) -> bool:
        normalized_code = code.strip()
        if not normalized_code:
            return False
        payload = await self._runtime_record_storage.get_record_by_fields(
            FindRuntimeRecordQuery(
                tenant_id=domain_id.value,
                object_name_singular=self.OBJECT_NAME,
                filters={
                    "domain_id": domain_id.value,
                    "code": normalized_code,
                },
            )
        )
        return payload is not None

    def _map_payload(self, payload: RuntimeRecordPayload) -> LinkEntity:
        values = payload.values
        created_at = values.get("created_at")
        domain_id = values.get("domain_id")
        code = values.get("code")

        if domain_id is None:
            raise ValidationError(
                f"shorter_link '{payload.record_id}' has no domain_id value"
            )
        if code is None:
            raise ValidationError(
                f"shorter_link '{payload.record_id}' has no code value"
            )

        parsed_domain_id = (
            domain_id if isinstance(domain_id, UUID) else UUID(str(domain_id))
        )
        return LinkEntity(
            id=LinkIdVO.from_value(payload.record_id),
            created_at=self._coerce_datetime(
                value=created_at,
                context=f"shorter_link '{payload.record_id}'",
            ),
            domain_id=EntityIdVO.from_value(parsed_domain_id),
            code=str(code).strip(),
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


__all__ = ["RuntimeRecordLinkRepository"]
