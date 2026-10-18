from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class ContentBlockSnapshot:
    """Неизменяемое определение разрешённого контентного блока."""

    id: EntityIdVO
    code: str
    value_type: str
    required: bool
    position: int
    label: str | None = None


@dataclass(frozen=True, slots=True)
class ProductTypeSchemaSnapshot:
    """Снимок tenant-схемы для проверки контента и чтения её подписей."""

    id: EntityIdVO
    code: str
    schema_version: int
    blocks: tuple[ContentBlockSnapshot, ...]
    label: str | None = None

    def validate_content(self, values: dict[str, str]) -> None:
        """Проверяет разрешённые коды, обязательность и ограничения текстовых значений."""
        allowed = {block.code: block for block in self.blocks}
        if values.keys() - allowed.keys():
            raise InvalidCatalogValueError(
                "Блок отсутствует в схеме товара.", ("content",)
            )
        for block in self.blocks:
            value = values.get(block.code)
            if block.required and (
                value is None or not isinstance(value, str) or not value.strip()
            ):
                raise InvalidCatalogValueError(
                    "Обязательный блок должен содержать текст.", ("content",)
                )
            if value is not None and (
                not isinstance(value, str)
                or len(value) > (255 if block.value_type == "text" else 1_000_000)
            ):
                raise InvalidCatalogValueError(
                    "Превышено ограничение текстового блока.", ("content",)
                )
