from uuid import uuid5
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from decimal import Decimal
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
from uuid import UUID
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
    CatalogDraftCheckDTO,
    CatalogCandidateDTO,
    CatalogCandidatesDTO,
)
from src.modules.catalog.application.catalog_item.facade import (
    CatalogItemsFacadeProtocol,
)
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
    CreateCatalogItemTranslation,
)
from src.modules.catalog.domain.error import CatalogError, CatalogNotFoundError
from src.modules.channels.domain.error import (
    ChannelsError,
    ChannelsNotFoundError,
    ChannelsDraftValidationError,
)


def values_for_catalog(values: CatalogDraftValuesDTO) -> CreateCatalogItemValues:
    """Передаёт только разрешённые значения нового Draft, не идентичность платформы."""
    if values.regular_price is None and (
        values.sale_price is not None or values.currency is not None
    ):
        raise InvalidCatalogValueError(
            "Без базовой цены нельзя переносить скидку или валюту.", ("price",)
        )
    if values.regular_price is not None and values.currency is None:
        raise InvalidCatalogValueError("Укажите валюту цены.", ("currency",))
    return CreateCatalogItemValues(
        sku=values.sku,
        price_specification=(
            PriceSpecificationVO(
                exact_decimal(values.regular_price),
                values.currency,
                (
                    exact_decimal(values.sale_price)
                    if values.sale_price is not None
                    else None
                ),
            )
            if values.regular_price is not None
            else None
        ),
        stock=StockSpecificationVO.from_declared_values(
            values.manage_stock, values.quantity, values.stock_status, values.backorders
        ),
        translations={
            code: CreateCatalogItemTranslation(
                {
                    "title": title,
                    **(
                        {"body": values.descriptions[code]}
                        if code in values.descriptions
                        else {}
                    ),
                }
            )
            for code, title in values.titles.items()
        },
        galleries={
            code: CatalogItemGallery.create(
                tuple(
                    CatalogItemImage.create(
                        EntityIdVO(uuid5(image.file_id, code + ":" + image.image_id)),
                        EntityIdVO(image.file_id),
                        position,
                        image.alt,
                    )
                    for position, image in enumerate(values.image_files)
                ),
                next(
                    (
                        EntityIdVO(uuid5(image.file_id, code + ":" + image.image_id))
                        for image in values.image_files
                        if image.image_id == values.primary_image_id
                    ),
                    None,
                ),
            )
            for code in values.titles
            if values.image_files
        },
    )


def exact_decimal(value: Decimal) -> Decimal:
    """Удаляет незначащие нули без округления контекстом Decimal."""
    sign, digits, exponent = value.as_tuple()
    if not value.is_finite():
        return value
    while len(digits) > 1 and digits[-1] == 0 and exponent < 0:
        digits, exponent = digits[:-1], exponent + 1
    return Decimal((sign, digits, exponent))


def mapped_catalog_error(error: CatalogError) -> ChannelsError:
    """Не пропускает исключения другого контекста через порт потребителя."""
    if isinstance(error, CatalogNotFoundError):
        return ChannelsNotFoundError("catalog_item_not_found")
    return ChannelsDraftValidationError(
        tuple((field, str(error)) for field in error.fields or ("draft",))
    )


class CatalogAdapter:
    """Изолирует ядро Channels от публичных DTO/ошибок владельца Catalog."""

    def __init__(self, facade: CatalogItemsFacadeProtocol) -> None:
        """Принимает фасад без SQL session, ORM или commit."""
        self.facade = facade

    async def validate(
        self, tenant_id: UUID, actor_id: UUID, values: CatalogDraftValuesDTO
    ) -> CatalogDraftCheckDTO:
        """Возвращает ошибки и вычисленное наличие без создания товара."""
        try:
            canonical = values_for_catalog(values)
        except CatalogError as error:
            return CatalogDraftCheckDTO(
                tuple((field, str(error)) for field in error.fields or ("draft",)), None
            )
        try:
            result = await self.facade.validate_draft(tenant_id, actor_id, canonical)
        except CatalogError as error:
            raise mapped_catalog_error(error) from error
        return CatalogDraftCheckDTO(result.issues, result.stock_status)

    async def create(
        self, tenant_id: UUID, actor_id: UUID, values: CatalogDraftValuesDTO
    ) -> UUID:
        """Вызывает самостоятельный атомарный use case Catalog на общем UoW."""
        try:
            return (
                await self.facade.create_item(
                    tenant_id, actor_id, values_for_catalog(values)
                )
            ).id
        except CatalogError as error:
            raise mapped_catalog_error(error) from error

    async def candidates(
        self, tenant_id: UUID, locale: str, search: str | None, offset: int, limit: int
    ) -> CatalogCandidatesDTO:
        """Преобразует страницу публичного read-сценария Catalog."""
        try:
            page = await self.facade.candidates(
                tenant_id, locale, search, offset, limit
            )
        except CatalogError as error:
            raise mapped_catalog_error(error) from error
        return CatalogCandidatesDTO(
            tuple(
                CatalogCandidateDTO(i.id, i.title, i.sku, i.status.value)
                for i in page.items
            ),
            page.total,
        )

    async def lock_item(self, tenant_id: UUID, item_id: UUID) -> str:
        """Принимает только разрешённый результат item-lock владельца."""
        try:
            return (await self.facade.lock_item(tenant_id, item_id)).status
        except CatalogError as error:
            raise mapped_catalog_error(error) from error
