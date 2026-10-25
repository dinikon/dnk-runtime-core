from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)

TERMINAL = frozenset(
    {"cancelled", "completed", "completed_with_errors", "failed", "expired"}
)
EXECUTING = frozenset({"queued", "running", "cancelling"})


@dataclass(slots=True)
class CatalogImport:
    """Жизненный цикл одного подтверждённого импорта без загрузки всех строк."""

    id: EntityIdVO
    actor_id: EntityIdVO
    idempotency_key: str
    fingerprint: str
    source_name: str
    source_url: str | None
    source_file_id: EntityIdVO | None
    configuration: ImportConfiguration
    status: str
    version: int
    prepared_version: int
    total: int
    processed: int
    created: int
    updated: int
    skipped: int
    errors: int
    warnings: int
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    job_id: EntityIdVO | None
    error: str | None

    @classmethod
    def create(
        cls,
        *,
        identifier: EntityIdVO,
        actor_id: EntityIdVO,
        key: str,
        fingerprint: str,
        name: str,
        url: str | None,
        file_id: EntityIdVO | None,
        configuration: ImportConfiguration,
        now: datetime,
    ) -> Self:
        """Создаёт подготовку нового неизменяемого источника."""
        if not key or len(key) > 200 or not name or len(name) > 255:
            raise InvalidCatalogValueError("Некорректное имя или ключ импорта.")
        entity = cls(
            identifier,
            actor_id,
            key,
            fingerprint,
            name,
            url,
            file_id,
            configuration,
            "preparing",
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            now,
            now,
            None,
            None,
            None,
        )
        entity._validate()
        return entity

    @classmethod
    def restore(
        cls,
        *,
        id: EntityIdVO,
        actor_id: EntityIdVO,
        idempotency_key: str,
        fingerprint: str,
        source_name: str,
        source_url: str | None,
        source_file_id: EntityIdVO | None,
        configuration: ImportConfiguration,
        status: str,
        version: int,
        prepared_version: int,
        total: int,
        processed: int,
        created: int,
        updated: int,
        skipped: int,
        errors: int,
        warnings: int,
        created_at: datetime,
        updated_at: datetime,
        finished_at: datetime | None,
        job_id: EntityIdVO | None,
        error: str | None,
    ) -> Self:
        """Восстанавливает сохранённое состояние; проверка переходов остаётся в методах."""
        entity = cls(
            id,
            actor_id,
            idempotency_key,
            fingerprint,
            source_name,
            source_url,
            source_file_id,
            configuration,
            status,
            version,
            prepared_version,
            total,
            processed,
            created,
            updated,
            skipped,
            errors,
            warnings,
            created_at,
            updated_at,
            finished_at,
            job_id,
            error,
        )
        entity._validate()
        return entity

    def _validate(self) -> None:
        """Защищает идентичности, версии, аудит и согласованность прогресса."""
        if (
            not isinstance(self.id, EntityIdVO)
            or not isinstance(self.actor_id, EntityIdVO)
            or any(
                value is not None and not isinstance(value, EntityIdVO)
                for value in (self.source_file_id, self.job_id)
            )
        ):
            raise InvalidCatalogValueError("Импорт требует доменные идентификаторы.")
        if self.status not in TERMINAL | EXECUTING | {
            "preparing",
            "mapping",
        } or not isinstance(self.configuration, ImportConfiguration):
            raise InvalidCatalogValueError("Некорректное состояние импорта.")
        counts = (
            self.total,
            self.processed,
            self.created,
            self.updated,
            self.skipped,
            self.errors,
            self.warnings,
        )
        if (
            any(type(value) is not int or value < 0 for value in counts)
            or self.processed > self.total
            or self.processed
            != self.created + self.updated + self.skipped + self.errors
        ):
            raise InvalidCatalogValueError("Прогресс импорта несогласован.")
        if (
            self.version < 1
            or not 0 <= self.prepared_version <= self.version
            or any(
                value.tzinfo is None or value.utcoffset() is None
                for value in (self.created_at, self.updated_at)
            )
        ):
            raise InvalidCatalogValueError("Версии и аудит импорта некорректны.")
        if self.status in TERMINAL and self.finished_at is None:
            raise InvalidCatalogValueError(
                "Завершённый импорт требует время завершения."
            )

    def configure(self, configuration: ImportConfiguration, now: datetime) -> None:
        """Меняет только ещё не запущенный черновик и инвалидирует подготовку."""
        if self.status != "mapping" and not (
            self.status == "failed"
            and self.total == 0
            and self.processed == 0
            and self.source_file_id is not None
        ):
            raise CatalogConflictError("Настройки запущенного импорта изменять нельзя.")
        self.configuration = configuration
        self.version += 1
        self.total = 0
        self.status, self.updated_at, self.error = "preparing", now, None
        self.finished_at = None

    def attach_source(self, file_id: EntityIdVO, now: datetime) -> None:
        """Фиксирует единственный снимок источника."""
        if self.source_file_id not in {None, file_id}:
            raise CatalogConflictError("Снимок источника уже зафиксирован.")
        self.source_file_id, self.updated_at = file_id, now

    def adopt_detected_configuration(
        self, configuration: ImportConfiguration, now: datetime
    ) -> None:
        """Принимает результат распознавания только незапущенной подготовки."""
        if self.status != "preparing":
            raise CatalogConflictError("Распознавание уже завершено.")
        self.configuration, self.updated_at = configuration, now

    def forget_source(self, now: datetime) -> EntityIdVO | None:
        """Снимает ссылку на истёкший источник только завершённого запуска."""
        if self.status not in TERMINAL:
            raise CatalogConflictError("Источник активного импорта очищать нельзя.")
        identifier = self.source_file_id
        self.source_file_id, self.source_url, self.updated_at = None, None, now
        return identifier

    def prepared(self, total: int, now: datetime) -> None:
        """Делает полностью разобранный снимок доступным для сопоставления."""
        if self.status != "preparing" or total < 0:
            raise CatalogConflictError("Подготовка уже завершена.")
        self.total, self.prepared_version = total, self.version
        self.status, self.updated_at = "mapping", now

    def schedule(self, job_id: EntityIdVO, now: datetime) -> None:
        """Сохраняет связанное задание в той же транзакции."""
        self.job_id, self.updated_at = job_id, now

    def start(self, version: int, now: datetime) -> bool:
        """Замораживает подтверждённую конфигурацию; повтор не создаёт новую работу."""
        if version != self.version:
            raise CatalogConflictError(
                "Предпросмотр изменился. Проверьте настройки ещё раз."
            )
        if self.status in TERMINAL and (
            not self.total or self.prepared_version != version
        ):
            raise CatalogConflictError("Этот источник не был подготовлен для запуска.")
        if (
            self.status in EXECUTING | TERMINAL
            and self.processed >= 0
            and self.status != "expired"
        ):
            return False
        if (
            self.status != "mapping"
            or self.prepared_version != version
            or not self.total
        ):
            raise CatalogConflictError("Дождитесь готового предпросмотра с записями.")
        self.configuration.ensure_startable()
        self.status, self.updated_at = "queued", now
        return True

    def begin(self, now: datetime) -> None:
        """Начинает или продолжает обработку активного запуска."""
        if self.status not in {"queued", "running"}:
            raise CatalogConflictError("Импорт не находится в очереди.")
        self.status, self.updated_at = "running", now

    def record(self, outcome: str, warnings: int, now: datetime) -> None:
        """Учитывает ровно один атомарно сохранённый результат строки."""
        if self.status != "running" or self.processed >= self.total:
            raise CatalogConflictError("Импорт не принимает результаты.")
        if outcome not in {"created", "updated", "skipped", "errors"} or warnings < 0:
            raise InvalidCatalogValueError("Неизвестный результат импорта.")
        setattr(self, outcome, getattr(self, outcome) + 1)
        self.processed += 1
        self.warnings += warnings
        self.updated_at = now
        if self.processed == self.total:
            self.status = "completed_with_errors" if self.errors else "completed"
            self.finished_at = now

    def cancel(self, now: datetime) -> None:
        """Запрашивает остановку либо сразу закрывает незапущенный черновик."""
        if self.status in TERMINAL:
            return
        self.status = "cancelling" if self.status in EXECUTING else "cancelled"
        self.updated_at = now
        if self.status == "cancelled":
            self.finished_at = now

    def stop(self, now: datetime) -> None:
        """Подтверждает остановку на границе позиции."""
        if self.status == "cancelling":
            self.status, self.finished_at, self.updated_at = "cancelled", now, now

    def fail(self, message: str, now: datetime) -> None:
        """Закрывает технически невосстановимый запуск."""
        if self.status not in TERMINAL:
            self.status, self.error = "failed", message[:1000]
            self.finished_at, self.updated_at = now, now

    def expire(self, now: datetime) -> None:
        """Закрывает неиспользованный черновик."""
        if self.status in {"mapping", "preparing"}:
            self.status, self.finished_at, self.updated_at = "expired", now, now
