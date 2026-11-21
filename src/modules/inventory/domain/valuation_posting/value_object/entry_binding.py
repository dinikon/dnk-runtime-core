from dataclasses import dataclass

from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_posting.error import (
    InvalidValuationEntryBindingError,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_id import (
    ValuationEntryIdVO,
)


@dataclass(frozen=True, slots=True)
class ValuationEntryBindingVO:
    """Назначает слою явно переданный идентификатор записи без генерации ID в Domain."""

    layer_id: ValuationLayerIdVO
    entry_id: ValuationEntryIdVO

    def __post_init__(self) -> None:
        """Проверяет номинальные идентификаторы привязки при создании значения."""
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Отклоняет сырые UUID и идентификаторы других видов."""
        if not isinstance(self.layer_id, ValuationLayerIdVO) or not isinstance(
            self.entry_id, ValuationEntryIdVO
        ):
            raise InvalidValuationEntryBindingError(
                "Нужны ValuationLayerIdVO и ValuationEntryIdVO."
            )
