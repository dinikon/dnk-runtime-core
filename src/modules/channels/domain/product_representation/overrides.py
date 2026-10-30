from dataclasses import dataclass
import re

from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.channels.domain.product_representation.value_object import ContentImage
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class LocalizedOverridesVO:
    """None означает наследование, пустые body и gallery — явную очистку."""

    locale: str
    title: str | None = None
    body: str | None = None
    gallery: tuple[ContentImage, ...] | None = None

    def __post_init__(self) -> None:
        """Проверяет собственные значения и отделяет галерею от входной коллекции."""
        if (
            not isinstance(self.locale, str)
            or len(self.locale) > 64
            or not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", self.locale)
        ):
            raise ProductRepresentationError("representation_locale_invalid")
        if self.title is not None and (
            not isinstance(self.title, str) or not self.title.strip()
        ):
            raise ProductRepresentationError("representation_title_invalid")
        if self.body is not None and not isinstance(self.body, str):
            raise ProductRepresentationError("representation_body_invalid")
        if self.gallery is not None:
            if not isinstance(self.gallery, (tuple, list)):
                raise ProductRepresentationError("representation_gallery_invalid")
            images = tuple(self.gallery)
            if any(
                not isinstance(image, ContentImage)
                or not isinstance(image.file_id, EntityIdVO)
                or not isinstance(image.alt, str)
                or not isinstance(image.caption, str)
                for image in images
            ):
                raise ProductRepresentationError("representation_gallery_invalid")
            if len({image.file_id for image in images}) != len(images):
                raise ProductRepresentationError("representation_gallery_duplicate")
            object.__setattr__(self, "gallery", images)

    @property
    def empty(self) -> bool:
        """Позволяет убрать пустую секцию, не теряя явную очистку."""
        return self.title is None and self.body is None and self.gallery is None


@dataclass(frozen=True, slots=True)
class ItemOverridesVO:
    """Связывает локализованные значения со стабильным ID пары."""

    binding_item_id: EntityIdVO
    content: tuple[LocalizedOverridesVO, ...]

    def __post_init__(self) -> None:
        """Отклоняет повтор локали и нормализует порядок значений."""
        if (
            not isinstance(self.binding_item_id, EntityIdVO)
            or not isinstance(self.content, (tuple, list))
            or any(
                not isinstance(value, LocalizedOverridesVO) for value in self.content
            )
        ):
            raise ProductRepresentationError("representation_item_invalid")
        if len({value.locale for value in self.content}) != len(self.content):
            raise ProductRepresentationError("representation_locale_duplicate")
        object.__setattr__(
            self,
            "content",
            tuple(
                sorted(
                    (value for value in self.content if not value.empty),
                    key=lambda value: value.locale,
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class RepresentationOverridesVO:
    """Каноническое неизменяемое намерение пользователя без словарей и Any."""

    common: tuple[LocalizedOverridesVO, ...] = ()
    items: tuple[ItemOverridesVO, ...] = ()

    def __post_init__(self) -> None:
        """Копирует коллекции, отклоняет дубли и убирает наследуемые секции."""
        if (
            not isinstance(self.common, (tuple, list))
            or not isinstance(self.items, (tuple, list))
            or any(not isinstance(value, LocalizedOverridesVO) for value in self.common)
            or any(not isinstance(value, ItemOverridesVO) for value in self.items)
        ):
            raise ProductRepresentationError("representation_overrides_invalid")
        if len({value.locale for value in self.common}) != len(self.common) or len(
            {value.binding_item_id for value in self.items}
        ) != len(self.items):
            raise ProductRepresentationError("representation_overrides_duplicate")
        object.__setattr__(
            self,
            "common",
            tuple(
                sorted(
                    (value for value in self.common if not value.empty),
                    key=lambda value: value.locale,
                )
            ),
        )
        object.__setattr__(
            self,
            "items",
            tuple(
                sorted(
                    (value for value in self.items if value.content),
                    key=lambda value: str(value.binding_item_id),
                )
            ),
        )

    def common_for(self, locale: str) -> LocalizedOverridesVO | None:
        """Возвращает только точную локаль общих overrides."""
        return next((value for value in self.common if value.locale == locale), None)

    def item_for(
        self, *, binding_item_id: EntityIdVO, locale: str
    ) -> LocalizedOverridesVO | None:
        """Возвращает значение пары без перехода к другому языку."""
        item = next(
            (value for value in self.items if value.binding_item_id == binding_item_id),
            None,
        )
        return (
            next((value for value in item.content if value.locale == locale), None)
            if item
            else None
        )

    def file_ids(self) -> tuple[EntityIdVO, ...]:
        """Собирает уникальные Files ID для пакетной проверки."""
        content = (
            *self.common,
            *(value for item in self.items for value in item.content),
        )
        return tuple(
            sorted(
                {image.file_id for value in content for image in value.gallery or ()},
                key=str,
            )
        )
