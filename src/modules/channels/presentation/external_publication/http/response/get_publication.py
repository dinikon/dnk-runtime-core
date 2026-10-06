from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.channels.application.external_publication.query.get_publication.dto import (
    PublicationImageDTO,
    PublicationCategoryDTO,
    PublicationAttributeDTO,
    PublicationVariantDTO,
    PublicationDetailsDTO,
)


class PublicationImageResponse(BaseModel):
    """Определяет HTTP поля сценария get_publication для PublicationImageDTO."""

    url: str
    alt: str

    @classmethod
    def from_dto(cls, dto: PublicationImageDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            url=dto.url,
            alt=dto.alt,
        )


class PublicationCategoryResponse(BaseModel):
    """Определяет HTTP поля сценария get_publication для PublicationCategoryDTO."""

    external_id: str
    name: str

    @classmethod
    def from_dto(cls, dto: PublicationCategoryDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            external_id=dto.external_id,
            name=dto.name,
        )


class PublicationAttributeResponse(BaseModel):
    """Определяет HTTP поля сценария get_publication для PublicationAttributeDTO."""

    name: str
    value: str
    unit: str | None

    @classmethod
    def from_dto(cls, dto: PublicationAttributeDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            name=dto.name,
            value=dto.value,
            unit=dto.unit,
        )


class PublicationVariantResponse(BaseModel):
    """Определяет HTTP поля сценария get_publication для PublicationVariantDTO."""

    id: UUID
    external_id: str
    title: str | None
    sku: str | None
    price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    availability: str | None
    source_status: str | None
    attributes: tuple[PublicationAttributeResponse, ...]

    @classmethod
    def from_dto(cls, dto: PublicationVariantDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            id=dto.id,
            external_id=dto.external_id,
            title=dto.title,
            sku=dto.sku,
            price=dto.price,
            currency=dto.currency,
            quantity=dto.quantity,
            availability=dto.availability,
            source_status=dto.source_status,
            attributes=tuple(
                PublicationAttributeResponse.from_dto(value) for value in dto.attributes
            ),
        )


class GetPublicationResponse(BaseModel):
    """Определяет HTTP поля сценария get_publication для PublicationDetailsDTO."""

    id: UUID
    channel_id: UUID
    external_id: str
    resource_type: str
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
    images: tuple[PublicationImageResponse, ...]
    categories: tuple[PublicationCategoryResponse, ...]
    attributes: tuple[PublicationAttributeResponse, ...]
    variants: tuple[PublicationVariantResponse, ...]
    expected_variations: int | None
    warnings: tuple[str, ...]
    schema_version: int
    revision: int
    observed_at: datetime

    @classmethod
    def from_dto(cls, dto: PublicationDetailsDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            id=dto.id,
            channel_id=dto.channel_id,
            external_id=dto.external_id,
            resource_type=dto.resource_type,
            title=dto.title,
            sku=dto.sku,
            external_url=dto.external_url,
            description_html=dto.description_html,
            short_description_html=dto.short_description_html,
            price=dto.price,
            regular_price=dto.regular_price,
            sale_price=dto.sale_price,
            currency=dto.currency,
            quantity=dto.quantity,
            availability=dto.availability,
            source_status=dto.source_status,
            product_type=dto.product_type,
            images=tuple(
                PublicationImageResponse.from_dto(value) for value in dto.images
            ),
            categories=tuple(
                PublicationCategoryResponse.from_dto(value) for value in dto.categories
            ),
            attributes=tuple(
                PublicationAttributeResponse.from_dto(value) for value in dto.attributes
            ),
            variants=tuple(
                PublicationVariantResponse.from_dto(value) for value in dto.variants
            ),
            expected_variations=dto.expected_variations,
            warnings=dto.warnings,
            schema_version=dto.schema_version,
            revision=dto.revision,
            observed_at=dto.observed_at,
        )
