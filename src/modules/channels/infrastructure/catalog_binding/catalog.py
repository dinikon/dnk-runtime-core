from datetime import datetime
from uuid import UUID
from src.modules.catalog.application.catalog_item.bindings_facade import (
    CatalogBindingsFacade,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    CatalogItemDetailsDTO,
)
from src.modules.channels.application.catalog_binding.contracts import (
    BindingPositionDTO,
    CatalogFamilyDTO,
    BindingCandidatesDTO,
    CatalogStructureDTO,
)
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingMode,
)


class CatalogBindingGateway:
    """Переводит только публичные DTO Catalog в собственные снимки Channels."""

    def __init__(self, facade: CatalogBindingsFacade) -> None:
        """Не читает Catalog ORM."""
        self.facade = facade

    async def lock(self, tenant_id: UUID, root_id: UUID) -> None:
        """Делегирует блокировку владельцу источника."""
        await self.facade.lock(tenant_id, root_id)

    @staticmethod
    def position(
        value: CatalogItemDetailsDTO, root_id: UUID, locale: str
    ) -> BindingPositionDTO:
        """Передаёт эффективные значения и авторизованный media endpoint владельца."""
        gallery = value.effective_gallery
        image = (
            next((i for i in gallery.images if i.id == gallery.primary_image_id), None)
            if gallery
            else None
        )
        prefix = f"/api/console/catalog/items/{root_id}"
        if value.kind == "variant":
            prefix += f"/variants/{value.id}"
        stock = value.effective_stock or value.stock
        return BindingPositionDTO(
            value.id,
            value.kind,
            (value.effective_content or {}).get("title"),
            value.sku,
            f"{prefix}/images/{locale}/{image.id}/content" if image else None,
            value.status.value,
            str(value.price) if value.price is not None else None,
            value.price_specification.currency if value.price_specification else None,
            str(stock.stock_quantity) if stock.stock_quantity is not None else None,
            value.stock_status,
            value.sources.stock if value.sources else value.id,
        )

    async def families(
        self, ids: tuple[UUID, ...], locale: str, now: datetime
    ) -> tuple[CatalogFamilyDTO, ...]:
        """Читает семьи batch без собственной сессии или транзакции."""
        snapshots = await self.facade.families(ids, locale, now)
        result = []
        for value in snapshots:
            positions = (
                value.variants if value.root.kind == "variable" else (value.root,)
            )
            result.append(
                CatalogFamilyDTO(
                    CatalogStructureDTO(
                        value.root.id, value.root.kind, tuple(v.id for v in positions)
                    ),
                    self.position(value.root, value.root.id, locale),
                    tuple(self.position(v, value.root.id, locale) for v in positions),
                )
            )
        return tuple(result)

    async def search(
        self,
        tenant_id: UUID,
        mode: BindingMode,
        locale: str,
        search: str,
        offset: int,
        limit: int,
        now: datetime,
    ) -> BindingCandidatesDTO:
        """Сохраняет серверную пагинацию и типовую фильтрацию владельца."""
        page = await self.facade.search(
            tenant_id=tenant_id,
            kind="simple" if mode is BindingMode.SIMPLE_TO_SIMPLE else "variable",
            locale=locale,
            search=search,
            offset=offset,
            limit=limit,
            as_of=now,
        )
        items = tuple(
            BindingPositionDTO(
                v.id,
                v.kind,
                v.title,
                v.sku,
                None,
                v.status.value,
                str(v.price) if v.price is not None else None,
                v.currency,
                None,
                v.stock_status,
                v.id,
            )
            for v in page.items
        )
        return BindingCandidatesDTO(items, (), page.total, page.offset, page.limit)
