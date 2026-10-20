from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.publication_import.value_object.snapshot import (
    ImportSnapshotVO,
    PreparedImageVO,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)


@dataclass(slots=True)
class PublicationImportPreparation:
    """Управляет снимком импорта и временными файлами до атомарного создания товара."""

    id: EntityIdVO
    publication_id: EntityIdVO
    actor_id: EntityIdVO
    connection_generation: int
    observed_revision: int
    status: str
    revision: int
    sequence: int
    snapshot: ImportSnapshotVO | None
    media: dict[str, PreparedImageVO]
    error_code: str | None
    created_at: datetime
    expires_at: datetime
    used_image_ids: tuple[str, ...]

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        publication_id: EntityIdVO,
        actor_id: EntityIdVO,
        generation: int,
        observed_revision: int,
        now: datetime,
    ) -> Self:
        """Создаёт ограниченную по времени подготовку без изменений Catalog."""
        return cls.restore(
            identifier,
            publication_id,
            actor_id,
            generation,
            observed_revision,
            "queued",
            1,
            0,
            None,
            {},
            None,
            now,
            now + timedelta(hours=24),
            (),
        )

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        publication_id: EntityIdVO,
        actor_id: EntityIdVO,
        generation: int,
        observed_revision: int,
        status: str,
        revision: int,
        sequence: int,
        snapshot: ImportSnapshotVO | None,
        media: dict[str, PreparedImageVO],
        error_code: str | None,
        created_at: datetime,
        expires_at: datetime,
        used_image_ids: tuple[str, ...],
    ) -> Self:
        """Восстанавливает процесс, проверяя lifecycle и принадлежность результатов снимку."""
        if any(
            not isinstance(value, EntityIdVO)
            for value in (identifier, publication_id, actor_id)
        ):
            raise ChannelsValidationError("invalid_import_identifier")
        if (
            status
            not in (
                "queued",
                "reading",
                "images",
                "ready",
                "error",
                "consumed",
                "expired",
                "cancelled",
            )
            or revision < 1
            or sequence < 0
            or generation < 0
            or observed_revision < 1
            or created_at.utcoffset() is None
            or expires_at <= created_at
        ):
            raise ChannelsValidationError("invalid_import_preparation")
        if (
            (snapshot is None and media)
            or (snapshot is not None and set(media) != {i.id for i in snapshot.images})
            or (status in ("images", "ready", "consumed") and snapshot is None)
        ):
            raise ChannelsValidationError("invalid_import_preparation")
        if not set(used_image_ids) <= set(media):
            raise ChannelsValidationError("invalid_import_preparation")
        return cls(
            identifier,
            publication_id,
            actor_id,
            generation,
            observed_revision,
            status,
            revision,
            sequence,
            snapshot,
            dict(media),
            error_code,
            created_at,
            expires_at,
            used_image_ids,
        )

    def ensure_current(
        self, now: datetime, expected_revision: int | None = None
    ) -> None:
        """Запрещает изменение истёкшего либо устаревшего предпросмотра."""
        if now >= self.expires_at or self.status in ("expired", "cancelled"):
            raise ChannelsConflictError("import_preparation_expired")
        if expected_revision is not None and self.revision != expected_revision:
            raise ChannelsConflictError("import_preparation_revision_conflict")

    def begin(self, sequence: int, now: datetime) -> bool:
        """Допускает повтор того же durable шага, игнорируя поздние worker-ответы."""
        if (
            now >= self.expires_at
            or sequence != self.sequence
            or self.status not in ("queued", "reading", "images")
        ):
            return False
        if self.status == "queued":
            self.status = "images" if self.snapshot else "reading"
            self.revision += 1
        return True

    def receive_snapshot(self, snapshot: ImportSnapshotVO) -> None:
        """Закрепляет полный снимок один раз перед обработкой его галереи."""
        if self.snapshot is not None or self.status != "reading":
            raise ChannelsConflictError("import_snapshot_already_received")
        self.snapshot = snapshot
        self.media = {image.id: PreparedImageVO() for image in snapshot.images}
        self.status = "images"
        self.advance()

    def pending_image(self) -> str | None:
        """Возвращает первое ещё не обработанное фото в порядке источника."""
        return (
            next(
                (
                    image.id
                    for image in self.snapshot.images
                    if self.media[image.id].file_id is None
                    and self.media[image.id].error_code is None
                ),
                None,
            )
            if self.snapshot
            else None
        )

    def receive_image(self, image_id: str, result: PreparedImageVO) -> None:
        """Фиксирует только ожидаемый результат текущего ограниченного шага."""
        if self.status != "images" or image_id != self.pending_image():
            raise ChannelsConflictError("import_image_step_conflict")
        if result.file_id is None and result.error_code is None:
            raise ChannelsValidationError("import_image_result_missing")
        self.media[image_id] = result
        self.advance()

    def advance(self) -> None:
        """Переходит к следующему job либо готовому предпросмотру с явными ошибками фото."""
        self.sequence += 1
        self.revision += 1
        if self.pending_image() is None:
            self.status = "ready"

    def fail(self, error_code: str) -> None:
        """Сохраняет безопасную причину сбоя без тела ответа и credentials."""
        self.status, self.error_code = "error", error_code
        self.revision += 1

    def retry(
        self, expected_revision: int, now: datetime, *, interrupted: bool = False
    ) -> None:
        """Повторяет чтение или ошибочные фотографии, сохраняя уже готовые файлы."""
        self.ensure_current(now, expected_revision)
        if (
            self.status not in ("error", "ready")
            and not (interrupted and self.status in ("queued", "reading", "images"))
        ) or (
            self.status == "ready"
            and not any(m.error_code for m in self.media.values())
        ):
            raise ChannelsConflictError("import_preparation_not_retryable")
        self.media = {
            key: PreparedImageVO(value.file_id) for key, value in self.media.items()
        }
        self.status, self.error_code = "queued", None
        self.sequence += 1
        self.revision += 1

    def consume(
        self, expected_revision: int, image_ids: tuple[str, ...], now: datetime
    ) -> None:
        """Передаёт выбранные готовые файлы товару в общей SQL-транзакции."""
        self.ensure_current(now, expected_revision)
        if (
            self.status != "ready"
            or len(set(image_ids)) != len(image_ids)
            or any(
                key not in self.media or self.media[key].file_id is None
                for key in image_ids
            )
        ):
            raise ChannelsConflictError("import_gallery_not_ready")
        self.status, self.used_image_ids = "consumed", image_ids
        self.revision += 1

    def cancel(self, expected_revision: int, now: datetime) -> None:
        """Закрывает подготовку без удаления её файлов внутри Domain."""
        self.ensure_current(now, expected_revision)
        if self.status == "consumed":
            raise ChannelsConflictError("import_preparation_already_used")
        self.status = "cancelled"
        self.revision += 1

    def expire(self, now: datetime) -> None:
        """Делает заброшенную подготовку недоступной для позднего создания."""
        if now < self.expires_at:
            raise ChannelsConflictError("import_preparation_not_expired")
        if self.status != "consumed":
            self.status = "expired"
            self.revision += 1

    def cleaned(self, image_ids: tuple[str, ...]) -> None:
        """Забывает только временные файлы после подтверждённой безопасной очистки."""
        if any(key in self.used_image_ids for key in image_ids):
            raise ChannelsConflictError("import_image_already_adopted")
        for key in image_ids:
            self.media[key] = PreparedImageVO(error_code="temporary_file_released")
        self.revision += 1
