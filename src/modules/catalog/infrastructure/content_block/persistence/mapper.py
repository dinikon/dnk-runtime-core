from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockCodeVO,
    ContentBlockIdVO,
    ContentBlockTranslationVO,
    ContentBlockType,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_definition import (
    ContentBlockDefinitionModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)


class ContentBlockMapper:
    """Преобразует определение блока между Domain и SQL-моделями."""

    @staticmethod
    def to_domain(
        row: ContentBlockDefinitionModel,
        translations: list[ContentBlockTranslationModel],
    ) -> ContentBlockDefinition:
        return ContentBlockDefinition.create(
            id=ContentBlockIdVO.from_value(row.id),
            code=ContentBlockCodeVO(row.code),
            type=ContentBlockType(row.type),
            is_system=row.is_system,
            translations={
                item.locale_code: ContentBlockTranslationVO(item.name)
                for item in translations
            },
        )

    @staticmethod
    def to_insert_values(block: ContentBlockDefinition) -> dict[str, object]:
        return {
            "id": block.id.uuid,
            "code": block.code.value,
            "type": block.type.value,
            "is_system": block.is_system,
        }

    @staticmethod
    def to_translation_values(block: ContentBlockDefinition) -> list[dict[str, object]]:
        return [
            {"block_id": block.id.uuid, "locale_code": code, "name": value.name}
            for code, value in block.translations.items()
        ]
