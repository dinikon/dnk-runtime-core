from dataclasses import dataclass
from datetime import datetime
import re
from typing import Self
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.catalog.domain.product_type.entity.content_block import ContentBlock
from src.modules.catalog.domain.product_type.value_object.defaults import (
    DEFAULT_BLOCKS,
    DEFAULT_PRODUCT_TYPE_CODE,
    DEFAULT_TYPE_LABELS,
)
from src.modules.catalog.domain.product_type.value_object.schema import (
    ContentBlockSnapshot,
    ProductTypeSchemaSnapshot,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ProductType:
    """Корень схемы контента с принадлежащими ей блоками и переводами."""

    id: EntityIdVO
    code: str
    schema_version: int
    is_system: bool
    blocks: tuple[ContentBlock, ...]
    labels: dict[str, str]
    created_by: EntityIdVO
    updated_by: EntityIdVO
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        code: str,
        blocks: tuple[ContentBlock, ...],
        labels: dict[str, str],
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт системную схему первой версии с переданными UUID блоков."""
        return cls.restore(
            identifier, code, 1, True, blocks, labels, actor_id, actor_id, now, now
        )

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        code: str,
        schema_version: int,
        is_system: bool,
        blocks: tuple[ContentBlock, ...],
        labels: dict[str, str],
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
        created_at: datetime,
        updated_at: datetime,
    ) -> Self:
        """Восстанавливает агрегат и проверяет уникальность состава и audit."""
        if (
            not all(
                isinstance(value, EntityIdVO)
                for value in (identifier, created_by, updated_by)
            )
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code)
            or type(schema_version) is not int
            or schema_version < 1
            or type(is_system) is not bool
        ):
            raise InvalidCatalogValueError(
                "Некорректная идентичность или версия ProductType."
            )
        if (
            not blocks
            or not all(isinstance(block, ContentBlock) for block in blocks)
            or any(
                len({getattr(block, name) for block in blocks}) != len(blocks)
                for name in ("id", "code", "position")
            )
        ):
            raise InvalidCatalogValueError(
                "Состав ProductType должен содержать уникальные блоки."
            )
        if any(
            value.tzinfo is None or value.utcoffset() is None
            for value in (created_at, updated_at)
        ):
            raise InvalidCatalogValueError("Audit требует timezone.")
        for locale, label in labels.items():
            LocaleVO(locale)
            if not isinstance(label, str) or not 1 <= len(label.strip()) <= 255:
                raise InvalidCatalogValueError("Некорректная подпись ProductType.")
        return cls(
            identifier,
            code,
            schema_version,
            is_system,
            tuple(sorted(blocks, key=lambda block: block.position)),
            dict(labels),
            created_by,
            updated_by,
            created_at,
            updated_at,
        )

    @staticmethod
    def validate_default_schema(schema: ProductTypeSchemaSnapshot) -> None:
        """Проверяет полноту системной схемы независимо от tenant UUID."""
        definition = tuple(
            (block.code, block.value_type, block.required, block.position)
            for block in schema.blocks
        )
        expected = tuple(
            (code, value_type, required, position)
            for position, (code, value_type, required, labels) in enumerate(
                DEFAULT_BLOCKS
            )
        )
        if (
            schema.code != DEFAULT_PRODUCT_TYPE_CODE
            or schema.schema_version != 1
            or definition != expected
        ):
            raise CatalogConflictError(
                "Системная схема Default установлена некорректно."
            )

    def ensure_default(self) -> None:
        """Проверяет идемпотентную установку полной системной схемы и её переводов."""
        self.validate_default_schema(self.snapshot())
        if (
            not self.is_system
            or self.labels != DEFAULT_TYPE_LABELS
            or any(
                block.labels != labels
                for block, (_, _, _, labels) in zip(self.blocks, DEFAULT_BLOCKS)
            )
        ):
            raise CatalogConflictError(
                "Системная схема Default установлена некорректно."
            )

    def snapshot(self, locale: str | None = None) -> ProductTypeSchemaSnapshot:
        """Возвращает схему без fallback между языками."""
        return ProductTypeSchemaSnapshot(
            self.id,
            self.code,
            self.schema_version,
            tuple(
                ContentBlockSnapshot(
                    block.id,
                    block.code,
                    block.value_type,
                    block.required,
                    block.position,
                    block.labels.get(locale),
                )
                for block in self.blocks
            ),
            self.labels.get(locale),
        )
