from dataclasses import dataclass

from src.modules.feed_builder.domain.export_state.error import InvalidExportStateError


@dataclass(frozen=True, slots=True)
class ExportCountsVO:
    """Считает позиции в трёх непересекающихся группах."""

    total_items: int = 0
    valid_items: int = 0
    warning_items: int = 0
    rejected_items: int = 0

    def __post_init__(self) -> None:
        """Проверяет неотрицательные счётчики и границу размера прохода."""
        if (
            any(
                type(value) is not int or value < 0
                for value in (
                    self.total_items,
                    self.valid_items,
                    self.warning_items,
                    self.rejected_items,
                )
            )
            or self.processed > self.total_items
        ):
            raise InvalidExportStateError("Несогласованные счётчики экспорта.")

    @property
    def processed(self) -> int:
        """Возвращает число проверенных позиций."""
        return self.valid_items + self.warning_items + self.rejected_items
