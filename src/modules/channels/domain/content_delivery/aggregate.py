from dataclasses import dataclass, field
from datetime import datetime
import re

from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.channels.domain.content_delivery.value_object import (
    DeliveryContextVO,
    DeliveryMediaVO,
    DeliveryStatus,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ContentDelivery:
    """Управляет поколениями доставки одной существующей внешней цели."""

    representation_id: EntityIdVO
    publication_id: EntityIdVO
    revision: int
    requested_generation: int
    sending_generation: int | None
    applied_generation: int | None
    status: DeliveryStatus
    current_job_id: EntityIdVO
    requested_context: DeliveryContextVO
    prepared_context: DeliveryContextVO | None
    prepared_media: tuple[DeliveryMediaVO, ...]
    prepared_schema: str | None
    prepared_request_encrypted: bytes | None = field(repr=False)
    prepared_hash: str | None
    last_applied_hash: str | None
    confirmed_fields: tuple[str, ...]
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        representation_id: EntityIdVO,
        publication_id: EntityIdVO,
        context: DeliveryContextVO,
        job_id: EntityIdVO,
        now: datetime,
    ) -> "ContentDelivery":
        """Создаёт первое ожидающее поколение без подготовленного запроса."""
        return cls.restore(
            representation_id=representation_id,
            publication_id=publication_id,
            revision=1,
            requested_generation=1,
            sending_generation=None,
            applied_generation=None,
            status=DeliveryStatus.QUEUED,
            current_job_id=job_id,
            requested_context=context,
            prepared_context=None,
            prepared_media=(),
            prepared_schema=None,
            prepared_request_encrypted=None,
            prepared_hash=None,
            last_applied_hash=None,
            confirmed_fields=(),
            error_code=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        representation_id: EntityIdVO,
        publication_id: EntityIdVO,
        revision: int,
        requested_generation: int,
        sending_generation: int | None,
        applied_generation: int | None,
        status: DeliveryStatus,
        current_job_id: EntityIdVO,
        requested_context: DeliveryContextVO,
        prepared_context: DeliveryContextVO | None,
        prepared_media: tuple[DeliveryMediaVO, ...],
        prepared_schema: str | None,
        prepared_request_encrypted: bytes | None,
        prepared_hash: str | None,
        last_applied_hash: str | None,
        confirmed_fields: tuple[str, ...],
        error_code: str | None,
        created_at: datetime,
        updated_at: datetime,
        completed_at: datetime | None,
    ) -> "ContentDelivery":
        """Проверяет сохранённое состояние целиком без исправления противоречий."""
        if (
            not isinstance(representation_id, EntityIdVO)
            or not isinstance(publication_id, EntityIdVO)
            or any(
                type(v) is not int or v < 1 for v in (revision, requested_generation)
            )
            or any(
                v is not None
                and (type(v) is not int or not 1 <= v <= requested_generation)
                for v in (sending_generation, applied_generation)
            )
            or not isinstance(status, DeliveryStatus)
            or not isinstance(current_job_id, EntityIdVO)
            or not isinstance(requested_context, DeliveryContextVO)
            or (
                prepared_context is not None
                and not isinstance(prepared_context, DeliveryContextVO)
            )
            or not isinstance(prepared_media, tuple)
            or any(not isinstance(v, DeliveryMediaVO) for v in prepared_media)
            or len({v.media_id for v in prepared_media}) != len(prepared_media)
            or any(
                v is not None
                and (not isinstance(v, str) or re.fullmatch(r"[0-9a-f]{64}", v) is None)
                for v in (prepared_hash, last_applied_hash)
            )
            or (
                error_code is not None
                and (
                    not isinstance(error_code, str)
                    or re.fullmatch(r"[a-z][a-z0-9_]{0,99}", error_code) is None
                )
            )
            or not isinstance(confirmed_fields, tuple)
            or any(v not in {"title", "body", "gallery"} for v in confirmed_fields)
            or len(set(confirmed_fields)) != len(confirmed_fields)
        ):
            raise ContentDeliveryError("content_state_invalid")
        prepared = prepared_context is not None
        if (
            any(
                (v is not None) != prepared
                for v in (
                    prepared_schema,
                    prepared_request_encrypted,
                    prepared_hash,
                    sending_generation,
                )
            )
            or (
                prepared
                and (
                    not isinstance(prepared_request_encrypted, bytes)
                    or not prepared_request_encrypted
                    or not isinstance(prepared_schema, str)
                    or not prepared_schema
                )
            )
            or (prepared_media and not prepared)
            or (
                status
                in {
                    DeliveryStatus.IN_FLIGHT,
                    DeliveryStatus.UNKNOWN,
                    DeliveryStatus.SUCCEEDED,
                }
                and not prepared
            )
            or (
                status
                in {
                    DeliveryStatus.UNKNOWN,
                    DeliveryStatus.FAILED,
                    DeliveryStatus.BLOCKED,
                }
            )
            != (error_code is not None)
            or (applied_generation is None) != (last_applied_hash is None)
            or (
                status
                in {
                    DeliveryStatus.QUEUED,
                    DeliveryStatus.BLOCKED,
                    DeliveryStatus.CANCELLED,
                }
                and prepared
            )
            or (status is DeliveryStatus.FAILED and not prepared)
            or (
                status
                in {
                    DeliveryStatus.SUCCEEDED,
                    DeliveryStatus.FAILED,
                    DeliveryStatus.UNKNOWN,
                }
                and completed_at is None
            )
            or (
                status
                in {
                    DeliveryStatus.QUEUED,
                    DeliveryStatus.IN_FLIGHT,
                    DeliveryStatus.BLOCKED,
                    DeliveryStatus.CANCELLED,
                }
                and completed_at is not None
            )
            or (
                status is DeliveryStatus.SUCCEEDED
                and (
                    applied_generation != sending_generation
                    or last_applied_hash != prepared_hash
                )
            )
        ):
            raise ContentDeliveryError("content_state_invalid")
        if (
            any(
                not isinstance(v, datetime) or v.utcoffset() is None
                for v in (created_at, updated_at)
            )
            or updated_at < created_at
            or (
                completed_at is not None
                and (
                    not isinstance(completed_at, datetime)
                    or completed_at.utcoffset() is None
                    or not created_at <= completed_at <= updated_at
                )
            )
        ):
            raise ContentDeliveryError("content_audit_invalid")
        return cls(
            representation_id=representation_id,
            publication_id=publication_id,
            revision=revision,
            requested_generation=requested_generation,
            sending_generation=sending_generation,
            applied_generation=applied_generation,
            status=status,
            current_job_id=current_job_id,
            requested_context=requested_context,
            prepared_context=prepared_context,
            prepared_media=prepared_media,
            prepared_schema=prepared_schema,
            prepared_request_encrypted=prepared_request_encrypted,
            prepared_hash=prepared_hash,
            last_applied_hash=last_applied_hash,
            confirmed_fields=confirmed_fields,
            error_code=error_code,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
        )

    def request_update(
        self, *, context: DeliveryContextVO, job_id: EntityIdVO, now: datetime
    ) -> bool:
        """Объединяет одинаковые активные запросы, не меняя выполняемый снимок."""
        self._require_time(now)
        if not isinstance(context, DeliveryContextVO) or not isinstance(
            job_id, EntityIdVO
        ):
            raise ContentDeliveryError("content_context_invalid")
        active = self.status in {
            DeliveryStatus.QUEUED,
            DeliveryStatus.IN_FLIGHT,
            DeliveryStatus.UNKNOWN,
        }
        if active and self.requested_context == context:
            return False
        self.requested_generation += 1
        self.requested_context = context
        if self.status not in {DeliveryStatus.IN_FLIGHT, DeliveryStatus.UNKNOWN}:
            self._queue(job_id)
        self.revision += 1
        self.updated_at = now
        return True

    def begin_attempt(
        self,
        *,
        job_id: EntityIdVO,
        encrypted_request: bytes,
        schema: str,
        content_hash: str,
        media: tuple[DeliveryMediaVO, ...],
        now: datetime,
    ) -> bool:
        """Фиксирует неизменяемый запрос до первого возможного сетевого побочного эффекта."""
        self._require_time(now)
        if self.current_job_id != job_id or self.status is not DeliveryStatus.QUEUED:
            return False
        if (
            not isinstance(encrypted_request, bytes)
            or not encrypted_request
            or not isinstance(schema, str)
            or not schema
            or not isinstance(content_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", content_hash) is None
            or not isinstance(media, tuple)
            or any(not isinstance(v, DeliveryMediaVO) for v in media)
            or len({v.media_id for v in media}) != len(media)
        ):
            raise ContentDeliveryError("content_request_invalid")
        self.prepared_context = self.requested_context
        self.prepared_media = media
        self.prepared_request_encrypted = encrypted_request
        self.prepared_schema = schema
        self.prepared_hash = content_hash
        self.sending_generation = self.requested_generation
        self.status = DeliveryStatus.IN_FLIGHT
        self.error_code = None
        self.completed_at = None
        self.revision += 1
        self.updated_at = now
        return True

    def complete_attempt(
        self,
        *,
        job_id: EntityIdVO,
        generation: int,
        content_hash: str,
        fields: tuple[str, ...],
        error_code: str | None,
        uncertain: bool,
        now: datetime,
        media: tuple[DeliveryMediaVO, ...] | None = None,
    ) -> bool:
        """Применяет только текущую попытку; новое намерение не считается выполненным."""
        self._require_time(now)
        if (
            self.current_job_id != job_id
            or self.sending_generation != generation
            or self.prepared_hash != content_hash
            or self.status not in {DeliveryStatus.IN_FLIGHT, DeliveryStatus.UNKNOWN}
        ):
            return False
        if (
            type(uncertain) is not bool
            or (uncertain and error_code is None)
            or (
                error_code is not None
                and (
                    not isinstance(error_code, str)
                    or re.fullmatch(r"[a-z][a-z0-9_]{0,99}", error_code) is None
                )
            )
            or not isinstance(fields, tuple)
            or any(v not in {"title", "body", "gallery"} for v in fields)
            or len(set(fields)) != len(fields)
        ):
            raise ContentDeliveryError("content_result_invalid")
        if media is not None and (
            not isinstance(media, tuple)
            or any(not isinstance(v, DeliveryMediaVO) for v in media)
            or {v.media_id for v in media} != {v.media_id for v in self.prepared_media}
            or len(media) != len(self.prepared_media)
        ):
            raise ContentDeliveryError("content_media_invalid")
        self.status = (
            DeliveryStatus.UNKNOWN
            if uncertain
            else (DeliveryStatus.FAILED if error_code else DeliveryStatus.SUCCEEDED)
        )
        self.error_code = error_code
        self.confirmed_fields = fields if error_code is None else ()
        if media is not None:
            self.prepared_media = media
        if error_code is None:
            self.applied_generation = generation
            self.last_applied_hash = content_hash
        self.completed_at = now
        self.revision += 1
        self.updated_at = now
        return True

    def queue_next(self, *, job_id: EntityIdVO, now: datetime) -> bool:
        """Продолжает только явно запрошенное новое поколение после известного исхода."""
        self._require_time(now)
        if (
            self.status in {DeliveryStatus.IN_FLIGHT, DeliveryStatus.UNKNOWN}
            or self.sending_generation is None
            or self.requested_generation <= self.sending_generation
        ):
            return False
        if not isinstance(job_id, EntityIdVO):
            raise ContentDeliveryError("content_context_invalid")
        self._queue(job_id)
        self.revision += 1
        self.updated_at = now
        return True

    def request_reconciliation(
        self, *, expected_revision: int, job_id: EntityIdVO, now: datetime
    ) -> None:
        """Меняет задание сверки, сохраняя исходный запрос и поколение."""
        self._require_time(now)
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise ContentDeliveryError("content_revision_conflict", conflict=True)
        if self.status is not DeliveryStatus.UNKNOWN or not isinstance(
            job_id, EntityIdVO
        ):
            raise ContentDeliveryError(
                "content_reconciliation_unavailable", conflict=True
            )
        self.current_job_id = job_id
        self.revision += 1
        self.updated_at = now

    def recover_queued(self, *, job_id: EntityIdVO, now: datetime) -> None:
        """Заменяет утраченное задание без создания нового пользовательского поколения."""
        self._require_time(now)
        if self.status is not DeliveryStatus.QUEUED or not isinstance(
            job_id, EntityIdVO
        ):
            raise ContentDeliveryError("content_attempt_active", conflict=True)
        self.current_job_id = job_id
        self.revision += 1
        self.updated_at = now

    def cancel(self, *, now: datetime) -> None:
        """Отменяет только ожидающую запись; начавшийся запрос нельзя откатить локально."""
        self._require_time(now)
        if self.status is DeliveryStatus.QUEUED:
            self.status = DeliveryStatus.CANCELLED
            self.error_code = None
            self.revision += 1
            self.updated_at = now

    def block(self, *, code: str, now: datetime) -> None:
        """Останавливает ещё не отправленный запрос без удаления последнего успеха."""
        self._require_time(now)
        if self.status is not DeliveryStatus.QUEUED:
            raise ContentDeliveryError("content_attempt_active", conflict=True)
        if (
            not isinstance(code, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{0,99}", code) is None
        ):
            raise ContentDeliveryError("content_result_invalid")
        self.status = DeliveryStatus.BLOCKED
        self.error_code = code
        self.revision += 1
        self.updated_at = now

    def _queue(self, job_id: EntityIdVO) -> None:
        """Очищает только текущую попытку; последний подтверждённый успех сохраняется."""
        self.current_job_id = job_id
        self.status = DeliveryStatus.QUEUED
        self.sending_generation = None
        self.prepared_context = None
        self.prepared_media = ()
        self.prepared_schema = None
        self.prepared_request_encrypted = None
        self.prepared_hash = None
        self.error_code = None
        self.completed_at = None

    def _require_time(self, now: datetime) -> None:
        """Проверяет аудит до первого изменения состояния."""
        if (
            not isinstance(now, datetime)
            or now.utcoffset() is None
            or now < self.updated_at
        ):
            raise ContentDeliveryError("content_audit_invalid")
