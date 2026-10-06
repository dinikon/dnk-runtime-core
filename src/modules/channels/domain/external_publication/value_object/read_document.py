from dataclasses import dataclass
from decimal import Decimal
from src.modules.channels.domain.external_publication.error import (
    InvalidPublicationError,
)


@dataclass(frozen=True, slots=True)
class PublicationImageVO:
    """Изображение внешней карточки с подписью."""

    url: str
    alt: str


@dataclass(frozen=True, slots=True)
class PublicationAttributeVO:
    """Наблюдаемая характеристика без привязки к атрибутам Catalog."""

    name: str
    value: str
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class PublicationCategoryVO:
    """Внешняя категория или группа товара."""

    external_id: str
    name: str


@dataclass(frozen=True, slots=True)
class PublicationReadDocumentVO:
    """Версионированный неизменяемый снимок полей для чтения карточки."""

    title: str | None
    sku: str | None
    external_url: str | None
    description_html: str | None
    short_description_html: str | None
    price: Decimal | None
    regular_price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    availability: str | None
    source_status: str | None
    product_type: str | None
    images: tuple[PublicationImageVO, ...]
    categories: tuple[PublicationCategoryVO, ...]
    attributes: tuple[PublicationAttributeVO, ...]
    expected_variations: int | None
    warnings: tuple[str, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        """Проверяет собственные значения неизменяемого Read документа."""
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise InvalidPublicationError("Unsupported document schema.")
        strings = (
            self.title,
            self.sku,
            self.external_url,
            self.description_html,
            self.short_description_html,
            self.currency,
            self.availability,
            self.source_status,
            self.product_type,
        )
        if any(value is not None and not isinstance(value, str) for value in strings):
            raise InvalidPublicationError("Invalid document text.")
        if any(
            value is not None
            and (not isinstance(value, Decimal) or not value.is_finite())
            for value in (
                self.price,
                self.regular_price,
                self.sale_price,
                self.quantity,
            )
        ):
            raise InvalidPublicationError("Invalid document number.")
        if self.expected_variations is not None and (
            type(self.expected_variations) is not int or self.expected_variations < 0
        ):
            raise InvalidPublicationError("Invalid variation count.")
        for values, expected in (
            (self.images, PublicationImageVO),
            (self.categories, PublicationCategoryVO),
            (self.attributes, PublicationAttributeVO),
            (self.warnings, str),
        ):
            if not isinstance(values, tuple) or any(
                not isinstance(value, expected) for value in values
            ):
                raise InvalidPublicationError("Mutable or invalid document values.")
