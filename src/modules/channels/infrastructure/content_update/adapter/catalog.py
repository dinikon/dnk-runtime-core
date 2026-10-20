from uuid import UUID
from src.modules.catalog.application.catalog_item.facade import (
    CatalogItemsFacadeProtocol,
)
from src.modules.catalog.domain.error import CatalogError
from src.modules.channels.domain.content_update.value_object.texts import (
    ContentTextsVO,
    LocalizedTextVO,
)
from src.modules.channels.domain.error import ChannelsConflictError


class CatalogContentAdapter:
    """Переиспользует item-lock и publication snapshot публичного фасада Catalog."""

    def __init__(self, facade: CatalogItemsFacadeProtocol) -> None:
        """Принимает существующий фасад без SQL и транзакционных методов."""
        self.facade = facade

    async def snapshot(
        self, tenant_id: UUID, item_ids: tuple[UUID, ...], locales: tuple[str, ...]
    ) -> dict[UUID, ContentTextsVO]:
        """Блокирует товары в устойчивом порядке и читает точные переводы."""
        values: dict[UUID, list[LocalizedTextVO]] = {
            identifier: [] for identifier in item_ids
        }
        try:
            for identifier in sorted(item_ids, key=str):
                await self.facade.lock_item(tenant_id, identifier)
            for locale in locales:
                result = await self.facade.publication_snapshot(
                    tenant_id, item_ids, locale
                )
                for item in result.items:
                    content = item.content or {}
                    values[item.id].append(
                        LocalizedTextVO(
                            locale, content.get("title"), content.get("body")
                        )
                    )
        except CatalogError as error:
            raise ChannelsConflictError("catalog_content_unavailable") from error
        return {
            identifier: ContentTextsVO(tuple(texts))
            for identifier, texts in values.items()
        }
