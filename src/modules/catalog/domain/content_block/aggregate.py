from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.value_object.code import CatalogCodeVO
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)


@dataclass(slots=True)
class ContentBlockDefinition:
    """Самостоятельное определение блока с версиями и переводами."""

    id: ContentBlockIdVO
    code: CatalogCodeVO
    is_system: bool
    translations: dict[str, str]
    value_type: ContentValueType
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        identifier: ContentBlockIdVO,
        code: str,
        value_type: ContentValueType,
        locale: LocaleVO,
        label: str,
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт пользовательский блок с явным типом и переводом."""
        cls._validate_label(label)
        return cls(
            identifier,
            CatalogCodeVO(code),
            False,
            {locale.value: label.strip()},
            value_type,
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
        identifier: ContentBlockIdVO,
        code: str,
        is_system: bool,
        translations: dict[str, str],
        value_type: ContentValueType,
        revision: int,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Восстанавливает определение, проверяя его собственные значения."""
        if revision < 1:
            raise InvalidCatalogValueError("Некорректная ревизия.")
        for locale, label in translations.items():
            LocaleVO(locale)
            cls._validate_label(label)
        return cls(
            identifier,
            CatalogCodeVO(code),
            is_system,
            dict(translations),
            value_type,
            revision,
            created_at,
            updated_at,
            created_by,
            updated_by,
        )

    def update_definition(
        self,
        value_type: ContentValueType,
        locale: LocaleVO,
        label: str,
        used: bool,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет подпись и тип; используемый тип нельзя менять несовместимо."""
        if used and value_type != self.value_type:
            raise CatalogConflictError("Тип используемого блока изменить нельзя.")
        self.put_translation(locale, label, actor, now)
        self.value_type = value_type

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
