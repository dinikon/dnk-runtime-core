from dataclasses import dataclass, replace
from datetime import datetime
from typing import Self
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.publication_import_run.value_object.identifier import (
    PublicationImportRunIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.publication_import_run.error import (
    InvalidPublicationImportError,
)


@dataclass(frozen=True, slots=True)
class PublicationImportRun:
    """Управляет прогрессом и завершением одного импорта подключения."""

    id: PublicationImportRunIdVO
    channel_id: ChannelIdVO
    connection_revision: int
    status: str
    checkpoint: str
    pages: int
    resources: int
    job_id: EntityIdVO
    error_code: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        id: PublicationImportRunIdVO,
        channel_id: ChannelIdVO,
        connection_revision: int,
        now: datetime,
    ) -> Self:
        """Создаёт очередь первой страницы с собственным идентификатором задания."""
        return cls.restore(
            id=id,
            channel_id=channel_id,
            connection_revision=connection_revision,
            status="queued",
            checkpoint="{}",
            pages=0,
            resources=0,
            job_id=EntityIdVO.from_value(id.uuid),
            error_code=None,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: PublicationImportRunIdVO,
        channel_id: ChannelIdVO,
        connection_revision: int,
        status: str,
        checkpoint: str,
        pages: int,
        resources: int,
        job_id: EntityIdVO,
        error_code: str | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> Self:
        """Проверяет статус, счётчики и границы времени сохранённого запуска."""
        if not (
            isinstance(id, PublicationImportRunIdVO)
            and isinstance(channel_id, ChannelIdVO)
            and type(job_id) is EntityIdVO
        ):
            raise InvalidPublicationImportError("Invalid import identifiers.")
        if status not in ("queued", "running", "succeeded", "partial", "failed"):
            raise InvalidPublicationImportError("Invalid import status.")
        if (
            any(
                type(value) is not int
                for value in (connection_revision, pages, resources)
            )
            or connection_revision < 1
            or pages < 0
            or resources < 0
            or not isinstance(checkpoint, str)
            or not checkpoint
            or (
                error_code is not None
                and (not isinstance(error_code, str) or not error_code)
            )
        ):
            raise InvalidPublicationImportError("Invalid import progress.")
        if (
            not isinstance(created_at, datetime)
            or not isinstance(updated_at, datetime)
            or created_at.utcoffset() is None
            or updated_at.utcoffset() is None
            or updated_at < created_at
        ):
            raise InvalidPublicationImportError("Invalid import time.")
        return cls(
            id,
            channel_id,
            connection_revision,
            status,
            checkpoint,
            pages,
            resources,
            job_id,
            error_code,
            created_at,
            updated_at,
        )

    @property
    def active(self) -> bool:
        """Показывает, допускается ли дальнейшее чтение страниц."""
        return self.status in ("queued", "running")

    def start(self, now: datetime) -> Self:
        """Начинает или продолжает ещё активный запуск."""
        if not self.active:
            raise InvalidPublicationImportError("Import is already finished.")
        self._validate_time(now)
        return replace(self, status="running", updated_at=now, error_code=None)

    def record_page(
        self, *, resources: int, checkpoint: str, job_id: EntityIdVO, now: datetime
    ) -> Self:
        """Атомарно продвигает прогресс после сохранения страницы."""
        self._validate_time(now)
        if (
            not self.active
            or type(resources) is not int
            or resources < 0
            or not isinstance(checkpoint, str)
            or not checkpoint
            or type(job_id) is not EntityIdVO
        ):
            raise InvalidPublicationImportError("Invalid page transition.")
        return replace(
            self,
            pages=self.pages + 1,
            resources=self.resources + resources,
            checkpoint=checkpoint,
            job_id=job_id,
            updated_at=now,
        )

    def finish(self, *, error_code: str | None, now: datetime) -> Self:
        """Завершает импорт, отличая частичные данные от полного успеха."""
        if not self.active:
            return self
        self._validate_time(now)
        if error_code is not None and (
            not isinstance(error_code, str) or not error_code
        ):
            raise InvalidPublicationImportError("Invalid completion reason.")
        status = (
            "succeeded"
            if error_code is None
            else ("partial" if self.resources else "failed")
        )
        return replace(self, status=status, error_code=error_code, updated_at=now)

    def _validate_time(self, now: datetime) -> None:
        """Защищает инвариант времени при каждом переходе агрегата."""
        if (
            not isinstance(now, datetime)
            or now.utcoffset() is None
            or now < self.updated_at
        ):
            raise InvalidPublicationImportError("Invalid import transition time.")
