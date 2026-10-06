from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.aggregate import (
    ContentScope,
    ProductType,
    ProductTypeContentBlock,
)
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_content_block import (
    ProductTypeContentBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_translation import (
    ProductTypeTranslationModel,
)


class ProductTypeMapper:
    """Восстанавливает ProductType и подготавливает значения для SQL."""

    @staticmethod
    def to_domain(
        row: ProductTypeModel,
        translations: list[ProductTypeTranslationModel],
        assignments: list[ProductTypeContentBlockModel],
    ) -> ProductType:
        return ProductType.restore(
            id=ProductTypeIdVO.from_value(row.id),
            code=row.code,
            is_system=row.is_system,
            schema_version=row.schema_version,
            translations={item.locale_code: item.name for item in translations},
            blocks=tuple(
                ProductTypeContentBlock(
                    ContentBlockIdVO.from_value(item.block_id),
                    ContentScope(item.scope),
                    item.required,
                    item.position,
                )
                for item in assignments
            ),
        )

    @staticmethod
    def to_insert_values(product_type: ProductType) -> dict[str, object]:
        return {
            "id": product_type.id.uuid,
            "code": product_type.code,
            "is_system": product_type.is_system,
            "schema_version": product_type.schema_version,
        }

    @staticmethod
    def to_translation_values(product_type: ProductType) -> list[dict[str, object]]:
        return [
            {"product_type_id": product_type.id.uuid, "locale_code": code, "name": name}
            for code, name in product_type.translations.items()
        ]

    @staticmethod
    def to_assignment_values(product_type: ProductType) -> list[dict[str, object]]:
        return [
            {
                "product_type_id": product_type.id.uuid,
                "scope": item.scope.value,
                "block_id": item.block_id.uuid,
                "required": item.required,
                "position": item.position,
            }
            for item in product_type.blocks
        ]
