"""Общие фабрики tenant-схем Catalog для тестов без фиксированных UUID."""

from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.application.product_type.facade import (
    CatalogProvisioningFacade,
)
from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.entity.content_block import ContentBlock
from src.modules.catalog.domain.product_type.value_object.defaults import (
    DEFAULT_BLOCKS,
    DEFAULT_TYPE_LABELS,
)
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
)
from src.modules.catalog.infrastructure.product_type.persistence.repository import (
    SqlAlchemyProductTypeRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator


def default_product_type() -> ProductType:
    """Создаёт независимый агрегат Default для unit-тестов."""
    return ProductType.create(
        EntityIdVO(uuid4()),
        "default",
        tuple(
            ContentBlock.create(
                EntityIdVO(uuid4()), code, kind, required, position, labels
            )
            for position, (code, kind, required, labels) in enumerate(DEFAULT_BLOCKS)
        ),
        DEFAULT_TYPE_LABELS,
        EntityIdVO(uuid4()),
        datetime(2026, 10, 18, tzinfo=UTC),
    )


def default_schema() -> ProductTypeSchemaSnapshot:
    """Возвращает полную схему с новыми идентификаторами на каждый вызов."""
    return default_product_type().snapshot()


async def initialize_catalog(
    session: AsyncSession, tenant_id: EntityIdVO, actor_id: EntityIdVO
) -> None:
    """Устанавливает Default через публичный фасад на внешней tenant-сессии."""
    await CatalogProvisioningFacade(
        SqlAlchemyProductTypeRepository(session), UUID7Generator(), UtcClock()
    ).initialize_defaults(tenant_id, actor_id)
