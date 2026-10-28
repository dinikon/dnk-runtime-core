from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def validate_content(values: dict[str, str]) -> None:
    """Проверяет форму сохранённых текстовых значений и каноническое имя товара."""
    if any(
        (
            not isinstance(value, str) or len(value) > 1000000
            for value in values.values()
        )
    ):
        raise InvalidCatalogValueError(
            "Контент требует текст до 1000000 символов.", ("content",)
        )
    if (
        "title" not in values
        or not values["title"].strip()
        or len(values["title"]) > 255
    ):
        raise InvalidCatalogValueError(
            "Title должен быть непустым текстом до 255 символов.", ("content",)
        )


def validate_gallery(gallery: CatalogItemGallery) -> None:
    """Проверяет идентичности, порядок и главное изображение всего набора."""
    images = gallery.images
    if (
        len(images) > 100
        or len({i.id for i in images}) != len(images)
        or len({i.file_id for i in images}) != len(images)
        or (len({i.position for i in images}) != len(images))
        or any(
            (
                type(i.position) is not int
                or i.position < 0
                or not isinstance(i.id, EntityIdVO)
                or not isinstance(i.file_id, EntityIdVO)
                or (len(i.alt) > 1000)
                or (len(i.caption) > 5000)
                for i in images
            )
        )
    ):
        raise InvalidCatalogValueError(
            "Некорректный состав или порядок галереи.", ("gallery",)
        )
    if bool(images) != (gallery.primary_image_id is not None) or (
        images and gallery.primary_image_id not in {i.id for i in images}
    ):
        raise InvalidCatalogValueError(
            "Непустая галерея требует главное изображение из своего набора.",
            ("gallery",),
        )
