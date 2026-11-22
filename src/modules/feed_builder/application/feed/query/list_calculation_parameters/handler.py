from src.modules.feed_builder.application.feed.query.list_calculation_parameters.query import (
    ListCalculationParametersQuery,
)
from src.modules.feed_builder.application.feed.query.list_calculation_parameters.dto import (
    ListCalculationParametersResultDTO,
    CalculationParameterDTO,
)
from src.modules.feed_builder.domain.feed.calculation.parameters import PARAMETER_TYPES


class ListCalculationParametersHandler:
    """Выдаёт параметры, проверяемые той же Domain Policy, что и preview/save."""

    async def execute(
        self, query: ListCalculationParametersQuery
    ) -> ListCalculationParametersResultDTO:
        """Не рекламирует неподключённые источники или защищённую закупку."""
        labels = {
            "price.regular": "Обычная цена",
            "price.sale": "Действующая акционная цена",
            "price.effective": "Текущая цена",
            "product.sku": "SKU позиции",
            "product.id": "ID позиции",
        }
        return ListCalculationParametersResultDTO(
            tuple(
                CalculationParameterDTO(name, labels[name], kind, name != "product.id")
                for name, kind in PARAMETER_TYPES
            )
        )
