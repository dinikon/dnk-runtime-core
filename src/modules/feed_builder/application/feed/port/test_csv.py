from collections.abc import Iterator
from typing import Protocol

from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)


class TestCsvFile(Protocol):
    """Предоставляет поток полностью подготовленного файла."""

    def chunks(self) -> Iterator[bytes]:
        """Читает части файла с начала."""
        ...

    def close(self) -> None:
        """Освобождает временный файл."""
        ...


class TestCsvWriter(TestCsvFile, Protocol):
    """Добавляет уже вычисленные записи к временной выгрузке."""

    def write(self, row: tuple[str | None, ...]) -> None:
        """Сериализует одну запись."""
        ...

    def finish(self) -> None:
        """Подготавливает файл к чтению."""
        ...


class TestCsvStorage(Protocol):
    """Создаёт изолированный временный файл одного запроса."""

    def open(self, settings: CsvExportSettingsVO) -> TestCsvWriter:
        """Открывает writer с настройками сохранённого Feed."""
        ...
