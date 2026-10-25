from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID
from dataclasses import asdict
from src.modules.crm.application.basket.values import (
    BasketInput,
    OwnerBasketProjection,
    BasketSummaryProjection,
)
from src.modules.crm.application.basket.port.query_repository import (
    BasketQueryRepositoryProtocol,
)
from src.modules.crm.application.basket.port.catalog_selection import (
    CatalogSelectionPort,
)
from src.modules.crm.domain.basket.aggregate import Basket
from src.modules.crm.domain.basket.entity.item import BasketItem
from src.modules.crm.domain.basket.repository import BasketRepositoryProtocol
from src.modules.crm.domain.sales_error import SalesError, SalesConflictError
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class BasketApplicationService:
    """Общая orchestration Basket без цепочек CRM handlers."""

    def __init__(
        self,
        repository: BasketRepositoryProtocol,
        reader: BasketQueryRepositoryProtocol,
        catalog: CatalogSelectionPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты на общей транзакции проверенного владельца."""
        self._repository = repository
        self._reader = reader
        self._catalog = catalog
        self._uuid = uuid

    async def _items(
        self, tenant_id: UUID, values: BasketInput, existing: Basket | None, locale: str
    ) -> tuple[tuple[BasketItem, ...], dict[str, UUID]]:
        """Проверяет принадлежность ID и получает снимки новых ссылок Catalog."""
        old = {i.id.uuid: i for i in existing.items} if existing else {}
        items = []
        mapping = {}
        keys = set()
        for value in values.items:
            if value.id is not None and value.id not in old:
                raise SalesError("Строка не принадлежит этой корзине.")
            if value.id is None and (
                not value.client_line_key or value.client_line_key in keys
            ):
                raise SalesError("Нужен уникальный client_line_key новой строки.")
            item_id = value.id or self._uuid.new()
            name = value.name
            sku = value.sku
            kind = value.kind
            if value.client_line_key:
                keys.add(value.client_line_key)
                mapping[value.client_line_key] = item_id
            if value.catalog_item_id and (
                value.id is None
                or value.catalog_item_id
                != (
                    old[value.id].catalog_item_id.uuid
                    if old[value.id].catalog_item_id
                    else None
                )
            ):
                snapshot = await self._catalog.get(
                    tenant_id, value.catalog_item_id, locale
                )
                name = name or snapshot.name
                sku = snapshot.sku
                kind = snapshot.kind
            items.append(
                BasketItem.create(
                    item_id=EntityIdVO(item_id),
                    name=name,
                    kind=kind,
                    quantity=value.quantity,
                    unit_price=value.unit_price,
                    unit=value.unit,
                    catalog_item_id=(
                        EntityIdVO(value.catalog_item_id)
                        if value.catalog_item_id
                        else None
                    ),
                    sku=sku,
                    custom_fields=value.custom_fields,
                )
            )
        return tuple(items), mapping

    async def create(
        self,
        model_key: str,
        owner_id: UUID,
        tenant_id: UUID,
        values: BasketInput,
        locale: str,
    ) -> tuple[UUID, dict[str, UUID]]:
        """Создаёт корзину только после проверки/создания владельца."""
        items, mapping = await self._items(tenant_id, values, None, locale)
        entity = Basket.create(
            basket_id=EntityIdVO(self._uuid.new()),
            owner_model_key=model_key,
            owner_record_id=EntityIdVO(owner_id),
            currency=values.currency,
            items=items,
        )
        await self._repository.add(entity)
        return entity.id.uuid, mapping

    async def replace(
        self,
        model_key: str,
        owner_id: UUID,
        tenant_id: UUID,
        values: BasketInput,
        locale: str,
    ) -> dict[str, UUID]:
        """Заменяет состав после блокировки и domain-проверки владельца."""
        entity = await self._repository.get_owner_for_update(
            model_key, EntityIdVO(owner_id)
        )
        if entity is None:
            raise SalesConflictError("Нарушена целостность: корзина отсутствует.")
        if values.expected_revision is None:
            raise SalesError("Нужна expected_revision корзины.")
        items, mapping = await self._items(tenant_id, values, entity, locale)
        entity.replace_items(
            currency=values.currency,
            items=items,
            expected_revision=values.expected_revision,
        )
        await self._repository.save(entity)
        return mapping

    async def get(self, model_key: str, owner_id: UUID) -> OwnerBasketProjection:
        """Читает согласованную проекцию; GET ничего не создаёт."""
        result = await self._reader.get_owner(model_key, owner_id)
        if result is None:
            raise SalesConflictError("Нарушена целостность: корзина отсутствует.")
        return result

    async def summaries(
        self, model_key: str, owner_ids: tuple[UUID, ...]
    ) -> dict[UUID, BasketSummaryProjection]:
        """Читает пакетную денежную сводку владельцев."""
        values = await self._reader.summaries(model_key, owner_ids)
        if len(values) != len(set(owner_ids)):
            raise SalesConflictError("Нарушена целостность корзин.")
        return values

    async def copy(self, source: Basket, target_id: UUID) -> UUID:
        """Создаёт независимую editable-копию с новыми ID строк."""
        items = tuple(
            BasketItem.create(
                item_id=EntityIdVO(self._uuid.new()),
                **{
                    k: getattr(i, k)
                    for k in (
                        "name",
                        "kind",
                        "catalog_item_id",
                        "sku",
                        "quantity",
                        "unit",
                        "unit_price",
                        "custom_fields",
                    )
                },
            )
            for i in source.items
        )
        entity = Basket.create(
            basket_id=EntityIdVO(self._uuid.new()),
            owner_model_key="crm.deal",
            owner_record_id=EntityIdVO(target_id),
            currency=source.currency,
            items=items,
            source_basket_id=source.id,
        )
        await self._repository.add(entity)
        return entity.id.uuid

    async def lock(self, model_key: str, owner_id: UUID) -> Basket:
        """Загружает агрегат для конвертации после блокировки владельца."""
        entity = await self._repository.get_owner_for_update(
            model_key, EntityIdVO(owner_id)
        )
        if entity is None:
            raise SalesConflictError("Корзина отсутствует.")
        return entity

    async def freeze(self, entity: Basket) -> None:
        """Фиксирует read-only состояние в текущем UoW."""
        entity.freeze()
        await self._repository.save(entity)
