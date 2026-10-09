from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.value_object.code import CatalogCodeVO
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.catalog.domain.product_type.value_object.block_link import (
    ProductTypeContentBlock,
)


@dataclass(slots=True)
class ProductType:
    """Самостоятельное определение схемы контента с версиями и переводами."""

    id: ProductTypeIdVO
    code: CatalogCodeVO
    is_system: bool
    translations: dict[str, str]
    schema_version: int
    blocks: tuple[ProductTypeContentBlock, ...]
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    def put_translation(
        self, locale: LocaleVO, label: str, actor: EntityIdVO, now: datetime
    ) -> None:
        """Меняет подпись одной locale без изменения идентичности."""
        if self.is_system:
            raise CatalogConflictError("Системное определение изменяется миграцией.")
        self._validate_label(label)
        self.translations[locale.value] = label.strip()
        self._touch(actor, now)

    @staticmethod
    def _validate_label(label: str) -> None:
        """Проверяет содержательную подпись определения."""
        if not isinstance(label, str) or not label.strip() or len(label) > 255:
            raise InvalidCatalogValueError("Подпись: от 1 до 255 символов.")

    def ensure_deletable(self, used: bool) -> None:
        """Защищает системное либо используемое определение от удаления."""
        if self.is_system or used:
            raise CatalogConflictError("Определение системное или используется.")

    def ensure_revision(self, expected: int) -> None:
        """Отклоняет запись из устаревшей ревизии."""
        if expected != self.revision:
            raise CatalogConflictError(
                "Ревизия изменилась. Загрузите актуальное состояние."
            )

    def _touch(self, actor: EntityIdVO, now: datetime) -> None:
        """Фиксирует ревизию и автора доменного изменения."""
        self.revision += 1
        self.updated_by = actor
        self.updated_at = now

    @staticmethod
    def validate_links(blocks: tuple[ProductTypeContentBlock, ...]) -> None:
        """Проверяет уникальность связи и порядка внутри каждого scope."""
        keys = [(b.block_id, b.scope) for b in blocks]
        positions = [(b.scope, b.position) for b in blocks]
        if len(keys) != len(set(keys)) or len(positions) != len(set(positions)):
            raise InvalidCatalogValueError(
                "Связи и позиции блоков должны быть уникальны внутри scope."
            )

    @classmethod
    def create(
        cls,
        identifier: ProductTypeIdVO,
        code: str,
        locale: LocaleVO,
        label: str,
        blocks: tuple[ProductTypeContentBlock, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт пользовательский тип с независимыми PRODUCT/VARIANT связями."""
        cls._validate_label(label)
        cls.validate_links(blocks)
        return cls(
            identifier,
            CatalogCodeVO(code),
            False,
            {locale.value: label.strip()},
            1,
            blocks,
            1,
            now,
            now,
            actor,
            actor,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: ProductTypeIdVO,
        code: str,
        is_system: bool,
        translations: dict[str, str],
        schema_version: int,
        blocks: tuple[ProductTypeContentBlock, ...],
        revision: int,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Восстанавливает тип, не изменяя версию и существующие связи."""
        if revision < 1 or schema_version < 1:
            raise InvalidCatalogValueError("Некорректная версия.")
        cls.validate_links(blocks)
        for locale, label in translations.items():
            LocaleVO(locale)
            cls._validate_label(label)
        return cls(
            identifier,
            CatalogCodeVO(code),
            is_system,
            dict(translations),
            schema_version,
            blocks,
            revision,
            created_at,
            updated_at,
            created_by,
            updated_by,
        )

    def replace_schema(
        self,
        blocks: tuple[ProductTypeContentBlock, ...],
        expected_schema_version: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Заменяет проверенную Application схему с защитой системного типа и версии."""
        if self.is_system:
            raise CatalogConflictError("Системная схема изменяется миграцией.")
        if self.schema_version != expected_schema_version:
            raise CatalogConflictError("Версия схемы изменилась.")
        self.validate_links(blocks)
        self.blocks = blocks
        self.schema_version += 1
        self._touch(actor, now)
