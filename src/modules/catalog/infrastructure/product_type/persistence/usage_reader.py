from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.infrastructure.persistence.models.content import (
    ProductContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_content_value import (
    ProductContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant_content_value import (
    VariantContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.persistence.models.variant_content import (
    VariantContentModel,
)


class SqlAlchemyProductTypeUsageReader:
    """Проверяет существующие товары и значения перед изменением схемы."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def type_in_use(self, type_id: ProductTypeIdVO) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(ProductModel.product_type_id == type_id.uuid))
            )
        )

    async def content_block_in_use(
        self, type_id: ProductTypeIdVO, scope: ContentScope, block_id: ContentBlockIdVO
    ) -> bool:
        if scope is ContentScope.PRODUCT:
            statement = select(
                exists()
                .select_from(ProductContentValueModel)
                .join(
                    ProductModel, ProductModel.id == ProductContentValueModel.product_id
                )
                .where(
                    ProductModel.product_type_id == type_id.uuid,
                    ProductContentValueModel.block_id == block_id.uuid,
                )
            )
        else:
            statement = select(
                exists()
                .select_from(VariantContentValueModel)
                .join(
                    VariantModel, VariantModel.id == VariantContentValueModel.variant_id
                )
                .join(ProductModel, ProductModel.id == VariantModel.product_id)
                .where(
                    ProductModel.product_type_id == type_id.uuid,
                    VariantContentValueModel.block_id == block_id.uuid,
                )
            )
        return bool(await self._session.scalar(statement))

    async def missing_required_value(
        self, type_id: ProductTypeIdVO, scope: ContentScope, block_id: ContentBlockIdVO
    ) -> bool:
        if scope is ContentScope.PRODUCT:
            statement = (
                select(ProductContentModel.product_id)
                .join(ProductModel, ProductModel.id == ProductContentModel.product_id)
                .where(
                    ProductModel.product_type_id == type_id.uuid,
                    ~exists().where(
                        ProductContentValueModel.product_id
                        == ProductContentModel.product_id,
                        ProductContentValueModel.locale_code
                        == ProductContentModel.locale_code,
                        ProductContentValueModel.block_id == block_id.uuid,
                    ),
                )
                .limit(1)
            )
        else:
            statement = (
                select(VariantContentModel.variant_id)
                .join(VariantModel, VariantModel.id == VariantContentModel.variant_id)
                .join(ProductModel, ProductModel.id == VariantModel.product_id)
                .where(
                    ProductModel.product_type_id == type_id.uuid,
                    ~exists().where(
                        VariantContentValueModel.variant_id
                        == VariantContentModel.variant_id,
                        VariantContentValueModel.locale_code
                        == VariantContentModel.locale_code,
                        VariantContentValueModel.block_id == block_id.uuid,
                    ),
                )
                .limit(1)
            )
        return (await self._session.scalar(statement)) is not None
