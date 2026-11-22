from collections.abc import Iterator
import csv
from io import TextIOWrapper
from tempfile import SpooledTemporaryFile

from src.modules.feed_builder.application.feed.port.test_csv import TestCsvWriter
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)


class _TemporaryCsv:
    """Держит небольшой файл в памяти и переносит большой во временное хранилище."""

    def __init__(self, settings: CsvExportSettingsVO) -> None:
        """Настраивает кодировку, разделитель и стандартное CSV-экранирование."""
        self._binary = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
        self._text = TextIOWrapper(self._binary, encoding=settings.encoding, newline="")
        self._writer = csv.writer(self._text, delimiter=settings.delimiter)

    def write(self, row: tuple[str | None, ...]) -> None:
        """Записывает значения без повторного форматирования."""
        self._writer.writerow(row)

    def finish(self) -> None:
        """Завершает кодирование перед чтением бинарного потока."""
        self._text.flush()
        self._binary.seek(0)

    def chunks(self) -> Iterator[bytes]:
        """Читает подготовленный файл ограниченными порциями."""
        try:
            while chunk := self._binary.read(64 * 1024):
                yield chunk
        finally:
            self.close()

    def close(self) -> None:
        """Закрывает и удаляет временный файл."""
        self._text.close()


class TemporaryCsvStorage:
    """Предоставляет временное хранилище пробного CSV."""

    def open(self, settings: CsvExportSettingsVO) -> TestCsvWriter:
        """Создаёт writer одного HTTP-запроса."""
        return _TemporaryCsv(settings)
