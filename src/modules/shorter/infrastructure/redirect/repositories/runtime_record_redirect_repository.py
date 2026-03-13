from __future__ import annotations

from datetime import datetime

from src.modules.runtime_record import (
    DeleteRuntimeRecordCommand,
    GetRuntimeRecordQuery,
    ListRuntimeRecordsQuery,
    RuntimeRecordPayload,
    RuntimeRecordStoragePort,
    UpsertRuntimeRecordCommand,
)
from src.modules.shared import EntityIdVO, ValidationError
from src.modules.shorter.domain.redirect import (
    RedirectEntity,
    RedirectIdVO,
    RedirectRepositoryPort,
    RedirectTargetUrlVO,
    RedirectUtmParametersVO,
)


class RuntimeRecordRedirectRepository(RedirectRepositoryPort):
    OBJECT_NAME = "shorter_redirect"

    def __init__(
        self,
        *,
        tenant_id: EntityIdVO,
        runtime_record_storage: RuntimeRecordStoragePort,
    ):
        self._tenant_id = tenant_id
        self._runtime_record_storage = runtime_record_storage

    async def save(self, redirect: RedirectEntity) -> None:
        await self._runtime_record_storage.upsert_record(
            UpsertRuntimeRecordCommand(
                tenant_id=self._tenant_id.value,
                object_name_singular=self.OBJECT_NAME,
                record_id=redirect.id.value,
                values={
                    "created_at": redirect.created_at,
                    "updated_at": redirect.updated_at,
                    "target_url": redirect.target_url.value,
                    "utm_source": redirect.utm_parameters.utm_source,
                    "utm_medium": redirect.utm_parameters.utm_medium,
                    "utm_campaign": redirect.utm_parameters.utm_campaign,
                    "utm_id": redirect.utm_parameters.utm_id,
                    "utm_term": redirect.utm_parameters.utm_term,
                    "utm_content": redirect.utm_parameters.utm_content,
                    "is_override": redirect.is_override,
                    "is_append": redirect.is_append,
                },
            )
        )

    async def get_by_id(
        self,
        *,
        redirect_id: RedirectIdVO,
    ) -> RedirectEntity | None:
        payload = await self._runtime_record_storage.get_record(
            GetRuntimeRecordQuery(
                tenant_id=self._tenant_id.value,
                object_name_singular=self.OBJECT_NAME,
                record_id=redirect_id.value,
            )
        )
        if payload is None:
            return None
        return self._map_payload(payload)

    async def list(self) -> tuple[RedirectEntity, ...]:
        payloads = await self._runtime_record_storage.list_records(
            ListRuntimeRecordsQuery(
                tenant_id=self._tenant_id.value,
                object_name_singular=self.OBJECT_NAME,
            )
        )
        return tuple(self._map_payload(payload) for payload in payloads)

    async def delete_by_id(
        self,
        *,
        redirect_id: RedirectIdVO,
    ) -> bool:
        return await self._runtime_record_storage.delete_record(
            DeleteRuntimeRecordCommand(
                tenant_id=self._tenant_id.value,
                object_name_singular=self.OBJECT_NAME,
                record_id=redirect_id.value,
            )
        )

    def _map_payload(self, payload: RuntimeRecordPayload) -> RedirectEntity:
        values = payload.values
        created_at = values.get("created_at")
        updated_at = values.get("updated_at")
        target_url = values.get("target_url")
        is_override = values.get("is_override")
        is_append = values.get("is_append")

        if target_url is None:
            raise ValidationError(
                f"shorter_redirect '{payload.record_id}' has no target_url value"
            )
        if is_override is None or is_append is None:
            raise ValidationError(
                f"shorter_redirect '{payload.record_id}' has invalid boolean flags"
            )

        return RedirectEntity(
            id=RedirectIdVO.from_value(payload.record_id),
            created_at=self._coerce_datetime(
                value=created_at,
                context=f"shorter_redirect '{payload.record_id}' created_at",
            ),
            updated_at=self._coerce_datetime(
                value=updated_at,
                context=f"shorter_redirect '{payload.record_id}' updated_at",
            ),
            target_url=RedirectTargetUrlVO(str(target_url)),
            utm_parameters=RedirectUtmParametersVO(
                utm_source=values.get("utm_source"),
                utm_medium=values.get("utm_medium"),
                utm_campaign=values.get("utm_campaign"),
                utm_id=values.get("utm_id"),
                utm_term=values.get("utm_term"),
                utm_content=values.get("utm_content"),
            ),
            is_override=self._coerce_bool(
                value=is_override,
                context=f"shorter_redirect '{payload.record_id}' is_override",
            ),
            is_append=self._coerce_bool(
                value=is_append,
                context=f"shorter_redirect '{payload.record_id}' is_append",
            ),
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

    @staticmethod
    def _coerce_bool(*, value: object, context: str) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in {0, 1}:
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1"}:
                return True
            if normalized in {"false", "0"}:
                return False
        raise ValidationError(f"{context} has invalid boolean value")


__all__ = ["RuntimeRecordRedirectRepository"]
