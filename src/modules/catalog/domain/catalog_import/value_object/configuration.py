from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from src.modules.catalog.domain.error import InvalidCatalogValueError

TARGETS = (
    "sku",
    "status",
    "virtual",
    "title",
    "body",
    "regular_price",
    "currency",
    "sale_price",
    "discount",
    "date_on_sale_from",
    "date_on_sale_to",
    "manage_stock",
    "stock_quantity",
    "stock_status",
    "backorders",
    "weight",
    "weight_unit",
    "length",
    "length_unit",
    "width",
    "width_unit",
    "height",
    "height_unit",
    "images",
    "image_alt",
    "image_caption",
    "primary_image",
)
LOCALIZED_TARGETS = frozenset(
    {"title", "body", "images", "image_alt", "image_caption", "primary_image"}
)


@dataclass(frozen=True, slots=True)
class ImportFieldMapping:
    """Одна явная связь источника или константы с полем товара."""

    target: str
    source: str | None = None
    constant: str | None = None
    locale: str | None = None

    def __post_init__(self) -> None:
        """Отклоняет неизвестные цели и неоднозначные источники."""
        if self.target not in TARGETS or (self.source is None) == (
            self.constant is None
        ):
            raise InvalidCatalogValueError(
                "Укажите поле и один источник либо константу."
            )
        if self.locale is not None and (
            not self.locale.strip() or len(self.locale) > 64
        ):
            raise InvalidCatalogValueError("Некорректная локаль сопоставления.")
        if self.locale is not None and self.target not in LOCALIZED_TARGETS:
            raise InvalidCatalogValueError(
                "Язык задаётся только для контента и галерей."
            )


@dataclass(frozen=True, slots=True)
class ImportConfiguration:
    """Подтверждаемые параметры разбора и применения значений."""

    mappings: tuple[ImportFieldMapping, ...] = ()
    mode: str = "create"
    clear_empty: bool = False
    default_locale: str = "uk"
    timezone: str = "Europe/Kyiv"
    encoding: str | None = None
    delimiter: str | None = None
    record_path: str | None = None

    def __post_init__(self) -> None:
        """Проверяет форму параметров, не выполняя I/O."""
        if (
            self.mode not in {"create", "update", "upsert"}
            or type(self.clear_empty) is not bool
        ):
            raise InvalidCatalogValueError("Некорректный режим импорта.")
        if self.encoding not in {None, "utf-8-sig", "utf-8", "cp1251"}:
            raise InvalidCatalogValueError("Неподдерживаемая кодировка.")
        if self.delimiter not in {None, ",", ";", "\t"}:
            raise InvalidCatalogValueError("Неподдерживаемый разделитель.")
        if not self.default_locale.strip() or len(self.default_locale) > 64:
            raise InvalidCatalogValueError("Укажите локаль импорта.")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise InvalidCatalogValueError("Неизвестный часовой пояс.") from error
        keys = [(m.target, m.locale or self.default_locale) for m in self.mappings]
        if len(keys) != len(set(keys)) or len(keys) > 500:
            raise InvalidCatalogValueError(
                "Поле назначения сопоставлено несколько раз."
            )
        images = [mapping for mapping in self.mappings if mapping.target == "images"]
        if len(images) > 1 and any(mapping.locale is None for mapping in images):
            raise InvalidCatalogValueError(
                "Выберите общие изображения либо отдельные галереи по языкам."
            )

    def ensure_startable(self) -> None:
        """Запрещает пустой запуск и обновление без ключа SKU."""
        if not self.mappings:
            raise InvalidCatalogValueError("Сопоставьте хотя бы одно поле.")
        if self.mode != "create" and not any(m.target == "sku" for m in self.mappings):
            raise InvalidCatalogValueError("Обновление требует сопоставить SKU.")
