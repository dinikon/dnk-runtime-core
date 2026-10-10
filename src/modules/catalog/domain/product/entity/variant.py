from dataclasses import dataclass
from typing import Self
from src.modules.catalog.domain.product.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.error import (
    CatalogDependencyUnavailableError,
    InvalidCatalogValueError,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO


@dataclass(slots=True)
class Variant:
    """Продаваемая позиция внутри Product; самостоятельного репозитория нет."""

    id: VariantIdVO
    virtual: bool
    downloadable: bool
    translations: dict[str, dict[str, str]]
    selection: VariationSelectionVO

    @classmethod
    def create(
        cls,
        identifier: VariantIdVO,
        virtual: bool,
        selection: VariationSelectionVO = VariationSelectionVO(),
    ) -> Self:
        """Создаёт позицию без SKU, файлов и переводов."""
        return cls.restore(identifier, virtual, False, {}, selection)

    @classmethod
    def restore(
        cls,
        identifier: VariantIdVO,
        virtual: bool,
        downloadable: bool,
        translations: dict[str, dict[str, str]],
        selection: VariationSelectionVO = VariationSelectionVO(),
    ) -> Self:
        """Восстанавливает позицию, отклоняя недоступное цифровое предложение."""
        if type(virtual) is not bool or type(downloadable) is not bool:
            raise InvalidCatalogValueError("Признаки позиции должны быть булевыми.")
        if not isinstance(identifier, VariantIdVO) or not isinstance(
            selection, VariationSelectionVO
        ):
            raise InvalidCatalogValueError(
                "Некорректная идентичность или selection позиции."
            )
        if downloadable:
            raise CatalogDependencyUnavailableError(
                "Downloadable требует файлового сервиса."
            )
        for locale in translations:
            LocaleVO(locale)
        return cls(
            identifier,
            virtual,
            downloadable,
            {k: dict(v) for k, v in translations.items()},
            selection,
        )

    def set_properties(self, virtual: bool, downloadable: bool) -> None:
        """Меняет независимые признаки; цифровая возможность требует контракта файлов."""
        if type(virtual) is not bool or type(downloadable) is not bool:
            raise InvalidCatalogValueError("Признаки позиции должны быть булевыми.")
        if downloadable:
            raise CatalogDependencyUnavailableError(
                "Downloadable требует файлового сервиса."
            )
        self.virtual = virtual
        self.downloadable = downloadable

    def put_content(self, locale: LocaleVO, values: dict[str, str]) -> None:
        """Сохраняет проверенный Product перевод конкретной позиции."""
        self.translations[locale.value] = dict(values)

    def delete_content(self, locale: LocaleVO) -> None:
        """Удаляет один перевод без наследования контента Product."""
        self.translations.pop(locale.value, None)
