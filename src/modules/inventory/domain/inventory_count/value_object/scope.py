from dataclasses import dataclass

from src.modules.inventory.domain.inventory_count.error import InvalidCountScopeError
from src.modules.inventory.domain.inventory_count.value_object.count_type import (
    CountType,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)


@dataclass(frozen=True, slots=True)
class CountScopeVO:
    """Область проверки: весь склад или непустой набор конкретных адресов без учёта порядка."""

    count_type: CountType
    location_ids: tuple[StockLocationIdVO, ...]

    def __post_init__(self) -> None:
        """Проверяет собственные значения и канонизирует порядок уникальных ID."""
        self.ensure_valid()
        object.__setattr__(
            self,
            "location_ids",
            tuple(
                sorted(self.location_ids, key=lambda identifier: identifier.uuid.int)
            ),
        )

    def ensure_valid(self) -> None:
        """Проверяет типы, уникальность и соответствие состава режиму без загрузки локаций."""
        if (
            not isinstance(self.count_type, CountType)
            or not isinstance(self.location_ids, tuple)
            or any(
                not isinstance(value, StockLocationIdVO) for value in self.location_ids
            )
        ):
            raise InvalidCountScopeError("Нужны CountType и tuple ID локаций.")
        if len(set(self.location_ids)) != len(self.location_ids):
            raise InvalidCountScopeError("Локации области не должны повторяться.")
        if (self.count_type is CountType.FULL and self.location_ids) or (
            self.count_type is CountType.PARTIAL and not self.location_ids
        ):
            raise InvalidCountScopeError(
                "FULL не перечисляет адреса, PARTIAL требует хотя бы один адрес."
            )
