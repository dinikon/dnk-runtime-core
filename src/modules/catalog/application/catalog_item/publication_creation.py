from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid5
from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
    CreateCatalogVariantValues,
    CreateCatalogItemTranslation,
)
from src.modules.catalog.application.catalog_item.port.sku import CatalogItemSkuPort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    WeightUnit,
    LengthVO,
    LengthUnit,
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class PublicationCatalogProductInput:
    """Публичный вход владельца Catalog без нативных полей площадки."""

    sku: str | None
    translations: dict[str, dict[str, str]]
    file_ids: tuple[UUID, ...]
    manage_stock: bool
    quantity: Decimal | None
    stock_status: str | None
    backorders: str
    virtual: bool
    weight: Decimal | None
    weight_unit: str | None
    length: Decimal | None
    width: Decimal | None
    height: Decimal | None
    dimension_unit: str | None
    regular_price: Decimal | None = None
    currency: str | None = None
    sale_price: Decimal | None = None
    date_on_sale_from: datetime | None = None
    date_on_sale_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class PublicationCatalogCreatedDTO:
    """Результат создания и порядок продаваемых позиций без Aggregate наружу."""

    root_id: UUID
    position_ids: tuple[UUID, ...]
    warnings: tuple[str, ...]


class PublicationCatalogCreation:
    """Публичный интерфейс создания на общей транзакции вызывающего процесса."""

    def __init__(
        self,
        *,
        creation: CatalogItemCreationService,
        repository: CatalogItemRepositoryProtocol,
        skus: CatalogItemSkuPort,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает собственные порты Catalog без SQL сессии."""
        self.creation, self.repository, self.skus, self.mutation_lock = (
            creation,
            repository,
            skus,
            lock,
        )

    async def lock(self, tenant_id: UUID, root_id: UUID) -> None:
        """Блокирует будущий корень до блокировки Channel."""
        await self.mutation_lock.acquire_item(
            EntityIdVO(tenant_id), CatalogItemIdVO(root_id)
        )

    @staticmethod
    def _values(
        product: PublicationCatalogProductInput, owner: UUID
    ) -> CreateCatalogVariantValues:
        """Преобразует публичные значения в собственную модель Catalog."""
        galleries = {}
        for locale in product.translations:
            images = tuple(
                CatalogItemImage.create(
                    EntityIdVO(uuid5(owner, f"{locale}:{file_id}")),
                    EntityIdVO(file_id),
                    index,
                )
                for index, file_id in enumerate(dict.fromkeys(product.file_ids))
            )
            if images:
                galleries[locale] = CatalogItemGallery.create(images, images[0].id)
        dimensions = None
        if product.dimension_unit:
            unit = LengthUnit(product.dimension_unit)
            dimensions = DimensionsVO(
                LengthVO(product.length, unit) if product.length is not None else None,
                LengthVO(product.width, unit) if product.width is not None else None,
                LengthVO(product.height, unit) if product.height is not None else None,
            )
        return CreateCatalogVariantValues(
            sku=product.sku,
            virtual=product.virtual,
            price_specification=(
                PriceSpecificationVO(
                    product.regular_price,
                    product.currency or "",
                    product.sale_price,
                    product.date_on_sale_from,
                    product.date_on_sale_to,
                )
                if product.regular_price is not None
                else None
            ),
            stock=StockSpecificationVO.from_declared_values(
                product.manage_stock,
                product.quantity,
                product.stock_status,
                product.backorders,
            ),
            translations={
                code: CreateCatalogItemTranslation(values)
                for code, values in product.translations.items()
                if values
            },
            galleries=galleries,
            weight=(
                WeightVO(product.weight, WeightUnit(product.weight_unit))
                if product.weight is not None and product.weight_unit
                else None
            ),
            dimensions=dimensions,
        )

    async def create(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        root_id: UUID,
        kind: str,
        root: PublicationCatalogProductInput,
        variants: tuple[PublicationCatalogProductInput, ...],
    ) -> PublicationCatalogCreatedDTO:
        """Очищает конфликтующие SKU и сохраняет целую карточку штатным сервисом."""
        products = tuple(
            replace(p, sku=SkuCodeVO(p.sku).value) if p.sku is not None else p
            for p in (root, *variants)
        )
        counts = Counter(p.sku for p in products if p.sku)
        conflicting: set[str] = set()
        for sku in sorted(counts):
            if counts[sku] > 1 or await self.skus.in_use(sku):
                conflicting.add(sku)
        warnings = (
            ("Конфликтующие SKU не перенесены: укажите новые значения в Catalog.",)
            if conflicting
            else ()
        )
        products = tuple(
            replace(p, sku=None) if p.sku in conflicting else p for p in products
        )
        values = tuple(
            self._values(p, uuid5(root_id, str(index)))
            for index, p in enumerate(products)
        )
        own = values[0]
        item = await self.creation.prepare(
            EntityIdVO(tenant_id),
            EntityIdVO(actor_id),
            CreateCatalogItemValues(
                kind=CatalogItemKind(kind),
                sku=own.sku,
                virtual=own.virtual,
                price_specification=own.price_specification,
                stock=own.stock,
                translations=own.translations,
                galleries=own.galleries,
                weight=own.weight,
                dimensions=own.dimensions,
                variants=values[1:],
            ),
            identifier=CatalogItemIdVO(root_id),
        )
        await self.repository.add(item)
        return PublicationCatalogCreatedDTO(
            item.id.uuid,
            tuple(v.id.uuid for v in item.variants) if variants else (item.id.uuid,),
            warnings,
        )
