from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.attribute.entity.option import AttributeOption
from src.modules.catalog.domain.value_object.label import CatalogLabelVO
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)


@dataclass(slots=True)
class AttributeDefinition:
    """Самостоятельное enum-определение; владеет options и их переводами."""

    id: AttributeIdVO
    translations: dict[str, str]
    options: tuple[AttributeOption, ...]

    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        identifier: AttributeIdVO,
        locale: LocaleVO,
        label: str,
        options: tuple[AttributeOption, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт определение с переводом и уникальными ID options."""
        return cls.restore(
            identifier=identifier,
            translations={locale.value: label},
            options=options,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: AttributeIdVO,
        translations: dict[str, str],
        options: tuple[AttributeOption, ...],
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Восстанавливает полный агрегат, отклоняя некорректное состояние."""
        cls._validate_options(options)
        values = {
            LocaleVO(k).value: CatalogLabelVO(v).value for k, v in translations.items()
        }
        return cls(
            identifier,
            values,
            options,
            created_at,
            updated_at,
            created_by,
            updated_by,
        )

    @staticmethod
    def _validate_options(options: tuple[AttributeOption, ...]) -> None:
        """Проверяет принадлежность сущностей и уникальность внутри определения."""
        if any(not isinstance(o, AttributeOption) for o in options):
            raise InvalidCatalogValueError("Ожидаются значения AttributeOption.")
        if len({o.id for o in options}) != len(options):
            raise InvalidCatalogValueError("ID options должны быть уникальны.")

    def get_option(self, identifier: AttributeOptionIdVO) -> AttributeOption:
        """Проверяет принадлежность option этому определению."""
        for option in self.options:
            if option.id == identifier:
                return option
        raise InvalidCatalogValueError("Option не принадлежит характеристике.")

    def put_translation(
        self, locale: LocaleVO, label: str, actor: EntityIdVO, now: datetime
    ) -> None:
        """Сохраняет подпись одной locale без смены идентичности."""
        value = CatalogLabelVO(label).value
        self.translations[locale.value] = value
        self._touch(actor, now)

    def replace_options(
        self,
        options: tuple[AttributeOption, ...],
        used_options: frozenset[AttributeOptionIdVO],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Меняет порядок и подписи, защищая идентичность и используемые значения."""
        self._validate_options(options)
        before = {o.id: o for o in self.options}
        after = {o.id: o for o in options}
        if (set(before) - set(after)) & used_options:
            raise CatalogConflictError("Удаляемое значение используется товарами.")
        self.options = options
        self._touch(actor, now)

    def ensure_deletable(self, used: bool) -> None:
        """Запрещает удаление определения, используемого товарами."""
        if used:
            raise CatalogConflictError("Характеристика используется товарами.")

    def _touch(self, actor: EntityIdVO, now: datetime) -> None:
        """Фиксирует автора и время изменения."""

        self.updated_by = actor
        self.updated_at = now
