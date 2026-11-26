from datetime import datetime
from html.parser import HTMLParser

from sqlalchemy.exc import DBAPIError

from src.modules.catalog.application.catalog_item.port.calculation_reader import (
    CatalogCalculationReference,
    CatalogPublicationValuesReaderProtocol,
)
from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationDependencyUnavailableError,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    CatalogReference,
)
from src.modules.feed_builder.domain.feed.expression.value_object.calculation_inputs import (
    CalculationInputsVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class _DescriptionText(HTMLParser):
    """Переводит богатое описание Catalog в обычный текст."""

    def __init__(self) -> None:
        """Накапливает текст и переносы абзацев."""
        super().__init__()
        self.parts: list[str] = []
        self._hidden_depth = 0

    def handle_data(self, data: str) -> None:
        """Сохраняет текстовое содержимое."""
        if not self._hidden_depth:
            self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Заменяет явный перенос обычным символом новой строки."""
        if tag in {"script", "style"}:
            self._hidden_depth += 1
        elif tag == "br" and not self._hidden_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Разделяет абзацы и элементы списка."""
        if tag in {"script", "style"} and self._hidden_depth:
            self._hidden_depth -= 1
        elif not self._hidden_depth and tag in {
            "p",
            "div",
            "li",
            "blockquote",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.parts.append("\n")


def _plain_description(value: str | None) -> str | None:
    """Возвращает содержимое текстовых узлов без HTML-разметки."""
    if value is None:
        return None
    parser = _DescriptionText()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts).removesuffix("\n")


class CatalogExportValues:
    """Адаптирует пакетный Application-контракт владельца товарных данных."""

    _codes = {"item.title": "title", "item.description": "body"}

    def __init__(self, reader: CatalogPublicationValuesReaderProtocol) -> None:
        """Сохраняет публичный порт Catalog."""
        self._reader = reader

    async def read(
        self,
        references: tuple[CatalogReference, ...],
        as_of: datetime,
        locales: frozenset[str],
        sources: frozenset[str],
    ) -> dict[CatalogReference, PublicationCatalogSnapshotVO]:
        """Переводит effective content и цены в снимки FeedBuilder."""
        try:
            items = await self._reader.read_publication_values(
                tuple(CatalogCalculationReference(*ref) for ref in references),
                as_of,
                locales,
                frozenset(self._codes[source] for source in sources),
            )
        except DBAPIError as exc:
            raise CalculationDependencyUnavailableError(
                "Catalog временно недоступен."
            ) from exc
        result: dict[CatalogReference, PublicationCatalogSnapshotVO] = {}
        for item in items:
            price = item.calculation
            result[(price.reference.item_id, price.reference.variant_id)] = (
                PublicationCatalogSnapshotVO(
                    inputs=CalculationInputsVO(
                        EntityIdVO(price.selected_id),
                        price.sku,
                        price.regular,
                        price.sale,
                        price.effective,
                        price.purchase,
                        tuple(EntityIdVO(category) for category in price.category_ids),
                        stock_quantity=price.stock_quantity,
                        in_stock=price.in_stock,
                    ),
                    texts=tuple(
                        (
                            ("item.description", locale, _plain_description(value))
                            if code == "body"
                            else ("item.title", locale, value)
                        )
                        for code, locale, value in item.texts
                    ),
                )
            )
        return result
