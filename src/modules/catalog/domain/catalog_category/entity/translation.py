from dataclasses import dataclass
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class CatalogCategoryTranslation:
    """Название узла на одном языке."""

    locale: LocaleVO
    name: str

    @classmethod
    def create(cls, locale: LocaleVO, name: str) -> "CatalogCategoryTranslation":
        """Создаёт название на выбранном языке каталога."""
        return cls.restore(locale, name)

    @classmethod
    def restore(cls, locale: LocaleVO, name: str) -> "CatalogCategoryTranslation":
        """Восстанавливает перевод с допустимым названием."""
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 255:
            raise InvalidCatalogValueError(
                "Название категории должно содержать от 1 до 255 символов."
            )
        return cls(locale, name.strip())
