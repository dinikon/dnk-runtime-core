from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.expression.value_object.calculation_inputs import (
    CalculationInputsVO,
)


@dataclass(frozen=True, slots=True)
class PublicationCatalogSnapshotVO:
    """Содержит данные выбранной позиции и эффективный текст по запрошенным локалям."""

    inputs: CalculationInputsVO
    texts: tuple[tuple[str, str, str | None], ...]

    def text(self, path: str, locale: str) -> str | None:
        """Возвращает эффективное значение в одной локали."""
        for source, language, value in self.texts:
            if (source, language) == (path, locale):
                return value
        return None
