import re
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from zoneinfo import ZoneInfo
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.application.catalog_import.contracts import SourceValues
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
    CreateCatalogItemTranslation,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockStatus,
    BackorderPolicy,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    WeightUnit,
    LengthVO,
    LengthUnit,
    DimensionsVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError

LOCALIZED = frozenset(
    {"title", "body", "images", "image_alt", "image_caption", "primary_image"}
)
STOCK = frozenset({"manage_stock", "stock_quantity", "stock_status", "backorders"})
PRICE = frozenset(
    {
        "regular_price",
        "currency",
        "sale_price",
        "discount",
        "date_on_sale_from",
        "date_on_sale_to",
    }
)


def mapped_values(
    configuration: ImportConfiguration, source: SourceValues
) -> SourceValues:
    """Выбирает явные поля; пропущенные источники никогда не очищают товар."""
    result: SourceValues = {}
    for mapping in configuration.mappings:
        if mapping.source is not None and mapping.source not in source:
            continue
        values = (
            [mapping.constant]
            if mapping.constant is not None
            else source.get(mapping.source or "", [])
        )
        if not configuration.clear_empty and not any(v.strip() for v in values):
            continue
        key = mapping.target
        if key in LOCALIZED:
            key += "@" + (mapping.locale or configuration.default_locale)
        result[key] = values
    return result


def scalar(values: SourceValues, key: str) -> str | None:
    """Читает одно значение, отклоняя неоднозначный массив для скалярного поля."""
    if key not in values:
        return None
    entries = values[key]
    if len(entries) != 1:
        raise InvalidCatalogValueError(
            f"{key}: выберите одно значение, найдено {len(entries)}.", (key,)
        )
    return entries[0].strip()


def decimal_value(value: str, field: str) -> Decimal:
    """Преобразует десятичную запятую и пробелы без float и округления."""
    try:
        result = Decimal(value.replace("\u00a0", "").replace(" ", "").replace(",", "."))
        if not result.is_finite():
            raise InvalidOperation
        return result
    except InvalidOperation as error:
        raise InvalidCatalogValueError(
            f"{field}: укажите корректное число.", (field,)
        ) from error


def boolean_value(value: str, field: str) -> bool:
    """Явно преобразует поддержанные написания, сохраняя strict bool в Domain."""
    key = value.lower()
    if key in {"true", "1", "yes", "да", "так"}:
        return True
    if key in {"false", "0", "no", "нет", "ні"}:
        return False
    if field == "virtual":
        if key in {"s", "@"}:
            return True
        if key in {"r", "w", "u"}:
            return False
    raise InvalidCatalogValueError(f"{field}: неизвестное boolean-значение.", (field,))


def stock_status_value(value: str) -> str:
    """Преобразует только подтверждённые статусы и обозначения Prom."""
    aliases = {
        "+": "in_stock",
        "!": "in_stock",
        "@": "in_stock",
        "true": "in_stock",
        "склад": "in_stock",
        "-": "out_of_stock",
        "&": "out_of_stock",
        "false": "out_of_stock",
        "": "out_of_stock",
        "under_the_order": "on_backorder",
    }
    normalized = aliases.get(
        value.lower(), "on_backorder" if value.isdigit() and int(value) > 0 else value
    )
    try:
        return StockStatus(normalized).value
    except ValueError as error:
        raise InvalidCatalogValueError(
            "Неизвестное наличие товара.", ("stock_status",)
        ) from error


def date_value(value: str | None, timezone: str, end: bool = False) -> datetime | None:
    """Переводит ISO и даты Prom в UTC, включая последний день скидки."""
    if not value:
        return None
    try:
        date_only = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4}", value))
        parsed = (
            datetime.strptime(value, "%d.%m.%Y")
            if "." in value and "T" not in value and " " not in value
            else datetime.fromisoformat(value.replace("Z", "+00:00"))
        )
        if end and date_only:
            parsed += timedelta(days=1)
        if parsed.tzinfo is None:
            zone = ZoneInfo(timezone)
            first = parsed.replace(tzinfo=zone, fold=0)
            second = parsed.replace(tzinfo=zone, fold=1)
            if (
                first.utcoffset() != second.utcoffset()
                or first.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != parsed
            ):
                raise ValueError("Ambiguous local time")
            parsed = first
        return parsed.astimezone(UTC)
    except ValueError as error:
        raise InvalidCatalogValueError(
            "Некорректная или неоднозначная дата скидки."
        ) from error


def image_urls(entries: list[str]) -> tuple[str, ...]:
    """Принимает повторяющиеся XML-теги, JSON-массив и список URL из Prom CSV."""
    result: list[str] = []
    for entry in entries:
        if entry.strip().startswith("["):
            try:
                parts = json.loads(entry)
                if not isinstance(parts, list) or any(
                    not isinstance(p, str) for p in parts
                ):
                    raise ValueError
            except (ValueError, TypeError) as error:
                raise InvalidCatalogValueError(
                    "Неверный список URL изображений.", ("images",)
                ) from error
        else:
            parts = re.split(r"[\r\n]+|[,;]\s*(?=https?://)", entry.strip())
        for part in parts:
            url = part.strip()
            if url and url not in result:
                result.append(url)
    return tuple(result)


def image_texts(entries: list[str]) -> list[str]:
    """Поддерживает одну подпись, повторяющиеся XML-поля и JSON-массив CSV."""
    if len(entries) == 1 and entries[0].lstrip().startswith("["):
        try:
            decoded = json.loads(entries[0])
        except ValueError:
            return entries
        if isinstance(decoded, list) and all(
            isinstance(value, str) for value in decoded
        ):
            return decoded
    return entries


@dataclass(frozen=True, slots=True)
class ImportProductValues:
    """Подготовленные полные группы значений и явный набор изменений."""

    product: CreateCatalogItemValues
    fields: frozenset[str]
    content_locales: frozenset[str]


def product_values(
    configuration: ImportConfiguration,
    values: SourceValues,
    current: CatalogItem | None = None,
) -> ImportProductValues:
    """Объединяет сопоставленные поля с актуальным товаром перед проверкой Domain."""
    product = (
        CreateCatalogItemValues()
        if current is None
        else CreateCatalogItemValues(
            virtual=current.virtual,
            status=current.status,
            sku=current.sku.value if current.sku else None,
            price_specification=current.price,
            stock=current.stock,
            weight=current.weight,
            dimensions=current.dimensions,
            translations={
                k: CreateCatalogItemTranslation(dict(v))
                for k, v in current.translations.items()
            },
        )
    )
    fields: set[str] = set()
    section = "product"
    try:
        if "sku" in values:
            section = "sku"
            product = replace(product, sku=scalar(values, "sku") or None)
            fields.add("sku")
        if "status" in values:
            section = "status"
            product = replace(
                product, status=CatalogItemStatus(scalar(values, "status"))
            )
            fields.add("status")
        if "virtual" in values:
            section = "virtual"
            product = replace(
                product,
                virtual=boolean_value(scalar(values, "virtual") or "", "virtual"),
            )
            fields.add("virtual")
        if values.keys() & PRICE:
            section = "price_specification"
            before = product.price_specification
            regular = (
                scalar(values, "regular_price")
                if "regular_price" in values
                else (str(before.regular_price) if before else None)
            )
            if regular == "":
                price = None
            else:
                if regular is None:
                    raise InvalidCatalogValueError(
                        "Цена требует обычную цену.", ("regular_price",)
                    )
                currency = (
                    scalar(values, "currency")
                    if "currency" in values
                    else (before.currency if before else "")
                )
                sale = (
                    scalar(values, "sale_price")
                    if "sale_price" in values
                    else (
                        str(before.sale_price)
                        if before and before.sale_price is not None
                        else None
                    )
                )
                amount = decimal_value(regular, "regular_price")
                discount = scalar(values, "discount")
                if discount:
                    with localcontext() as context:
                        context.prec = 100
                        reduction = decimal_value(discount.rstrip("%"), "discount")
                        if reduction < 0:
                            raise InvalidCatalogValueError(
                                "Скидка не может быть отрицательной."
                            )
                        sale = str(
                            amount
                            - (
                                amount * reduction / Decimal(100)
                                if discount.endswith("%")
                                else reduction
                            )
                        )
                start = (
                    date_value(
                        scalar(values, "date_on_sale_from"), configuration.timezone
                    )
                    if "date_on_sale_from" in values
                    else (before.date_on_sale_from if before else None)
                )
                end = (
                    date_value(
                        scalar(values, "date_on_sale_to"), configuration.timezone, True
                    )
                    if "date_on_sale_to" in values
                    else (before.date_on_sale_to if before else None)
                )
                if sale == "":
                    start = end = None
                price = PriceSpecificationVO(
                    amount,
                    currency or "",
                    decimal_value(sale, "sale_price") if sale else None,
                    start,
                    end,
                )
            product = replace(product, price_specification=price)
            fields.add("price_specification")
        if values.keys() & STOCK:
            section = "stock"
            before = product.stock
            quantity = scalar(values, "stock_quantity")
            status = scalar(values, "stock_status")
            manage = (
                boolean_value(scalar(values, "manage_stock") or "", "manage_stock")
                if "manage_stock" in values
                else (
                    True
                    if quantity
                    else False if status is not None else before.manage_stock
                )
            )
            policy = (
                scalar(values, "backorders")
                if "backorders" in values
                else (before.backorders.value if before.manage_stock else "no")
            )
            if status is not None:
                status = stock_status_value(status)
            if manage:
                if "stock_quantity" in values and quantity == "":
                    raise InvalidCatalogValueError(
                        "При включённом учёте количество нельзя очистить.",
                        ("stock_quantity",),
                    )
                if status == "on_backorder" and "backorders" not in values:
                    policy = "yes"
                q = (
                    decimal_value(quantity, "stock_quantity")
                    if quantity
                    else (
                        Decimal(before.stock_quantity)
                        if before.stock_quantity is not None
                        else None
                    )
                )
                stock = StockSpecificationVO.from_declared_values(
                    True, q, None, policy or "no"
                )
            else:
                if "backorders" in values and policy != "no":
                    raise InvalidCatalogValueError(
                        "Политика предзаказа требует количественного учёта.",
                        ("backorders",),
                    )
                if quantity:
                    raise InvalidCatalogValueError(
                        "Количество требует включённого учёта.", ("stock_quantity",)
                    )
                stock = StockSpecificationVO(
                    False,
                    None,
                    (
                        StockStatus(status)
                        if status is not None
                        else (before.stock_status or StockStatus.IN_STOCK)
                    ),
                    BackorderPolicy.NO,
                )
            product = replace(product, stock=stock)
            fields.add("stock")
        for name in ("weight", "length", "width", "height"):
            if name not in values and name + "_unit" not in values:
                continue
            section = name
            before_measure = (
                product.weight
                if name == "weight"
                else getattr(product.dimensions, name, None)
            )
            value = (
                scalar(values, name)
                if name in values
                else (str(before_measure.value) if before_measure else None)
            )
            unit = (
                scalar(values, name + "_unit")
                if name + "_unit" in values
                else (before_measure.unit.value if before_measure else None)
            )
            if value is None and before_measure is None and name not in values:
                continue
            if value is None:
                raise InvalidCatalogValueError(
                    f"{name}: отсутствует значение.", (name,)
                )
            measure = (
                None
                if value == ""
                else (
                    WeightVO(decimal_value(value, name), WeightUnit(unit))
                    if name == "weight"
                    else LengthVO(decimal_value(value, name), LengthUnit(unit))
                )
            )
            if name == "weight":
                product = replace(product, weight=measure)
                fields.add("weight")
            else:
                product = replace(
                    product,
                    dimensions=replace(
                        product.dimensions or DimensionsVO(), **{name: measure}
                    ),
                )
                fields.add("dimensions")
        section = "content"
        translations = dict(product.translations)
        locales = {
            key.split("@", 1)[1]
            for key in values
            if key.startswith(("title@", "body@"))
        }
        for locale in locales:
            content = (
                dict(translations[locale].values) if locale in translations else {}
            )
            for target in ("title", "body"):
                key = f"{target}@{locale}"
                if key in values:
                    # Rich text сохраняет исходные пробелы, как обычное редактирование.
                    entries = values[key]
                    if len(entries) != 1:
                        raise InvalidCatalogValueError(
                            f"{target}: выберите одно значение."
                        )
                    content[target] = entries[0]
            translations[locale] = CreateCatalogItemTranslation(content)
        product = replace(product, translations=translations)
        return ImportProductValues(product, frozenset(fields), frozenset(locales))
    except InvalidCatalogValueError as error:
        if error.fields:
            raise
        raise InvalidCatalogValueError(str(error), (section,)) from error
    except (ValueError, TypeError, InvalidOperation) as error:
        raise InvalidCatalogValueError(
            "Недопустимое значение поля или единицы измерения.", (section,)
        ) from error
