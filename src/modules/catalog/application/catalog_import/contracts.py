from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO, Protocol
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)

SourceValues = dict[str, list[str]]


class ImportMediaPort(Protocol):
    """Готовит проверенный Files ID либо безопасное предупреждение без SQL-контекста."""

    async def download(
        self, identifier: UUID, url: str
    ) -> tuple[UUID | None, str | None]:
        """Переиспользует уже подготовленное изображение данного импорта."""
        ...


@dataclass(frozen=True, slots=True)
class SourceField:
    """Стабильный идентификатор поля с отображаемой подписью."""

    id: str
    label: str


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """Одна запись без потери одинаковых заголовков и повторяющихся XML-полей."""

    number: int
    values: SourceValues


@dataclass(frozen=True, slots=True)
class SourceDescription:
    """Результат ограниченного потокового исследования источника."""

    format: str
    encoding: str | None
    delimiter: str | None
    record_path: str | None
    candidates: tuple[str, ...]
    fields: tuple[SourceField, ...]


class ImportParserPort(Protocol):
    """Читает CSV/XML без знания хранения и транзакций."""

    def inspect(
        self, source: BinaryIO, configuration: ImportConfiguration
    ) -> SourceDescription:
        """Определяет формат и допустимые параметры разбора."""
        ...

    def records(
        self, source: BinaryIO, description: SourceDescription
    ) -> Iterator[SourceRecord]:
        """Последовательно выдаёт записи с ограничением размера и количества."""
        ...


@dataclass(frozen=True, slots=True)
class ImportRowResult:
    """Атомарный результат одной позиции."""

    number: int
    outcome: str
    sku: str | None = None
    item_id: UUID | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ImportRowsPort(Protocol):
    """Техническое staging-хранилище и журнал, принадлежащие импорту."""

    async def reset(self, identifier: UUID) -> None:
        """Удаляет только ещё не запущенные исходные записи."""
        ...

    async def stage(self, identifier: UUID, rows: tuple[SourceRecord, ...]) -> None:
        """Идемпотентно сохраняет порцию исходных записей."""
        ...

    async def next_row(self, identifier: UUID) -> SourceRecord | None:
        """Возвращает первую необработанную запись."""
        ...

    async def finish(self, identifier: UUID, result: ImportRowResult) -> None:
        """Фиксирует единственный результат строки в общей транзакции."""
        ...

    async def duplicate(self, identifier: UUID, number: int, sku: str) -> bool:
        """Проверяет наличие уже встреченного SKU в предыдущих строках."""
        ...

    async def find_item(self, sku: str) -> UUID | None:
        """Разрешает SKU только в текущем tenant."""
        ...


class ImportQueuePort(Protocol):
    """Планирует идемпотентные задания в транзакции импорта."""

    async def schedule(
        self,
        identifier: EntityIdVO,
        version: int,
        cursor: int,
        kind: str,
        delay_seconds: int | None = None,
    ) -> EntityIdVO:
        """Возвращает ID единственного задания для этапа и курсора."""
        ...
