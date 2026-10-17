from dataclasses import dataclass
from typing import Self
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.value_object.label import CatalogLabelVO
from src.modules.catalog.domain.value_object.locale import LocaleVO


@dataclass(slots=True)
class AttributeOption:
    """Значение enum, принадлежащее AttributeDefinition."""

    id: AttributeOptionIdVO
    translations: dict[str, str]

    @classmethod
    def create(
        cls, identifier: AttributeOptionIdVO, locale: LocaleVO, label: str | None
    ) -> Self:
        """Создаёт значение с устойчивой идентичностью и явным переводом."""
        if label is None:
            raise InvalidCatalogValueError(
                "Новой опции нужно название выбранной locale."
            )
        return cls.restore(identifier, {locale.value: label})

    @classmethod
    def restore(
        cls, identifier: AttributeOptionIdVO, translations: dict[str, str]
    ) -> Self:
        """Восстанавливает подписи без подмены идентичности текстом."""
        values = {
            LocaleVO(k).value: CatalogLabelVO(v).value for k, v in translations.items()
        }
        return cls(identifier, values)

    def translated(self, locale: LocaleVO, label: str | None) -> Self:
        """Сохраняет перевод; None оставляет все локали без изменений."""
        translations = dict(self.translations)
        if label is not None:
            translations[locale.value] = label
        return self.restore(self.id, translations)
