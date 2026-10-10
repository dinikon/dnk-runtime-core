from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.attribute.entity.option import AttributeOption
from src.modules.catalog.domain.value_object.code import CatalogCodeVO
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
    code: CatalogCodeVO
    translations: dict[str, str]
    options: tuple[AttributeOption, ...]
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        identifier: AttributeIdVO,
        code: str,
        locale: LocaleVO,
        label: str,
        options: tuple[AttributeOption, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт определение с уникальными кодами и ID options."""
        return cls.restore(
            identifier=identifier,
            code=code,
            translations={locale.value: label},
            options=options,
            revision=1,
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
        code: str,
        translations: dict[str, str],
        options: tuple[AttributeOption, ...],
        revision: int,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Восстанавливает полный агрегат, отклоняя некорректное состояние."""
        if revision < 1:
            raise InvalidCatalogValueError("Некорректная ревизия.")
        cls._validate_options(options)
        values = {
            LocaleVO(k).value: CatalogLabelVO(v).value for k, v in translations.items()
        }
        return cls(
            identifier,
            CatalogCodeVO(code),
            values,
            options,
            revision,
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
        if len({o.id for o in options}) != len(options) or len(
            {o.code for o in options}
        ) != len(options):
            raise InvalidCatalogValueError("ID и коды options должны быть уникальны.")

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
        for identifier, option in after.items():
            if identifier in before and option.code != before[identifier].code:
                raise CatalogConflictError("Код существующего option изменить нельзя.")
        self.options = options
        self._touch(actor, now)

    def ensure_revision(self, expected: int) -> None:
        """Защищает агрегат от записи устаревшей формы."""
        if expected != self.revision:
            raise CatalogConflictError(
                "Ревизия изменилась. Загрузите актуальное состояние."
            )

    def ensure_deletable(self, used: bool) -> None:
        """Запрещает удаление определения, используемого товарами."""
        if used:
            raise CatalogConflictError("Характеристика используется товарами.")

    def _touch(self, actor: EntityIdVO, now: datetime) -> None:
        """Фиксирует автора и новую ревизию изменения."""
        self.revision += 1
        self.updated_by = actor
        self.updated_at = now
