from dataclasses import dataclass
from typing import Self
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.value_object.code import CatalogCodeVO
from src.modules.catalog.domain.value_object.label import CatalogLabelVO
from src.modules.catalog.domain.value_object.locale import LocaleVO


@dataclass(slots=True)
class AttributeOption:
    """Значение enum, принадлежащее AttributeDefinition."""

    id: AttributeOptionIdVO
    code: CatalogCodeVO
    translations: dict[str, str]

    @classmethod
    def create(
        cls, identifier: AttributeOptionIdVO, code: str, locale: LocaleVO, label: str
    ) -> Self:
        """Создаёт значение с устойчивой идентичностью и явным переводом."""
        return cls.restore(identifier, code, {locale.value: label})

    @classmethod
    def restore(
        cls, identifier: AttributeOptionIdVO, code: str, translations: dict[str, str]
    ) -> Self:
        """Восстанавливает подписи без подмены идентичности текстом."""
        values = {
            LocaleVO(k).value: CatalogLabelVO(v).value for k, v in translations.items()
        }
        return cls(identifier, CatalogCodeVO(code), values)

    def translated(self, locale: LocaleVO, label: str) -> Self:
        """Возвращает новую проверенную версию с сохранением других локалей."""
        return self.restore(
            self.id, self.code.value, {**self.translations, locale.value: label}
        )
