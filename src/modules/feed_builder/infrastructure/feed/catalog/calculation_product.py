from datetime import datetime
from uuid import UUID
from sqlalchemy.exc import DBAPIError
from src.modules.catalog.application.catalog_item.port.calculation_reader import (
    CatalogCalculationReaderProtocol,
    CatalogCalculationReference,
    CatalogCalculationItemNotFoundError,
)
from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationProductSnapshot,
    CalculationProductNotFoundError,
    CalculationDependencyUnavailableError,
)
from src.modules.feed_builder.domain.feed.value_object.calculation_inputs import (
    CalculationInputsVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogCalculationProductReader:
    """Адаптирует публичное чтение Catalog без SQL JOIN или импорта его Domain."""

    def __init__(self, reader: CatalogCalculationReaderProtocol) -> None:
        """Принимает owner-порт, собранный на той же tenant-сессии."""
        self._reader = reader

    async def read(
        self, item_id: UUID, variant_id: UUID | None, as_of: datetime
    ) -> CalculationProductSnapshot:
        """Сохраняет различие отсутствия позиции и технической недоступности."""
        try:
            result = (
                await self._reader.read_many(
                    (CatalogCalculationReference(item_id, variant_id),), as_of
                )
            )[0]
        except CatalogCalculationItemNotFoundError as exc:
            raise CalculationProductNotFoundError(str(exc)) from exc
        except DBAPIError as exc:
            raise CalculationDependencyUnavailableError(
                "Catalog временно недоступен."
            ) from exc
        return CalculationProductSnapshot(
            item_id=item_id,
            variant_id=variant_id,
            selected_id=result.selected_id,
            kind=result.kind,
            revision=result.revision,
            valid_until=result.valid_until,
            inputs=CalculationInputsVO(
                product_id=EntityIdVO(result.selected_id),
                sku=result.sku,
                regular=result.regular,
                sale=result.sale,
                effective=result.effective,
                purchase=result.purchase,
                category_ids=tuple(
                    EntityIdVO(category) for category in result.category_ids
                ),
            ),
        )
