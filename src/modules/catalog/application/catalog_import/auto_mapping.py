import re
from src.modules.catalog.application.catalog_import.contracts import SourceField
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportFieldMapping,
    TARGETS,
)

ALIASES: dict[str, tuple[str, str | None]] = {
    "кодтовару": ("sku", None),
    "кодтовара": ("sku", None),
    "vendorcode": ("sku", None),
    "назвапозиції": ("title", "ru"),
    "названиепозиции": ("title", "ru"),
    "name": ("title", "ru"),
    "назвапозиціїукр": ("title", "uk"),
    "названиепозицииукр": ("title", "uk"),
    "nameua": ("title", "uk"),
    "опис": ("body", "ru"),
    "описание": ("body", "ru"),
    "description": ("body", "ru"),
    "описукр": ("body", "uk"),
    "описаниеукр": ("body", "uk"),
    "descriptionua": ("body", "uk"),
    "ціна": ("regular_price", None),
    "цена": ("regular_price", None),
    "price": ("regular_price", None),
    "валюта": ("currency", None),
    "currencyid": ("currency", None),
    "наявність": ("stock_status", None),
    "наличие": ("stock_status", None),
    "available": ("stock_status", None),
    "availability": ("stock_status", None),
    "кількість": ("stock_quantity", None),
    "количество": ("stock_quantity", None),
    "quantityinstock": ("stock_quantity", None),
    "stockquantity": ("stock_quantity", None),
    "посиланнязображення": ("images", None),
    "ссылкаизображения": ("images", None),
    "picture": ("images", None),
    "знижка": ("discount", None),
    "скидка": ("discount", None),
    "терміндіїзнижкивід": ("date_on_sale_from", None),
    "срокдействияскидкиот": ("date_on_sale_from", None),
    "терміндіїзнижкидо": ("date_on_sale_to", None),
    "срокдействияскидкидо": ("date_on_sale_to", None),
    "вагакг": ("weight", None),
    "вескг": ("weight", None),
    "ширинасм": ("width", None),
    "висотасм": ("height", None),
    "высотасм": ("height", None),
    "довжинасм": ("length", None),
    "длинасм": ("length", None),
    "типтовару": ("virtual", None),
    "типтовара": ("virtual", None),
    "sellingtype": ("virtual", None),
}


def normalized(value: str) -> str:
    """Сравнивает только имена, не меняя идентичность столбцов."""
    return re.sub(r"[^\w]", "", value.lower()).replace("_", "")


def suggest_mappings(
    fields: tuple[SourceField, ...], default_locale: str
) -> tuple[ImportFieldMapping, ...]:
    """Предлагает детерминированные правила Prom и системных полей."""
    result: dict[tuple[str, str | None], ImportFieldMapping] = {}
    canonical = {normalized(t): t for t in TARGETS}
    old_price: str | None = None
    old_price_priority = 0
    price: str | None = None
    for field in fields:
        label = field.label.rsplit("/", 1)[-1].rsplit("}", 1)[-1].lstrip("@")
        key = normalized(label)
        if key in {"oldprice", "priceold"}:
            priority = 2 if label.lower() == "oldprice" else 1
            if priority > old_price_priority:
                old_price, old_price_priority = field.id, priority
            continue
        if key == "price":
            price = field.id
        found = ALIASES.get(key)
        # Canonical localized headers: translations.uk.title, title.uk, body.ru.
        localized = re.fullmatch(
            r"(?:translations\.)?([a-z]{2}(?:-[a-z0-9]+)?)\.(title|body|images|image_alt|image_caption)",
            field.label,
            re.I,
        )
        reverse = re.fullmatch(
            r"(title|body|images|image_alt|image_caption)\.([a-z]{2}(?:-[a-z0-9]+)?)",
            field.label,
            re.I,
        )
        if localized:
            found = (localized[2], localized[1])
        elif reverse:
            found = (reverse[1], reverse[2])
        elif found is None and key in canonical:
            target = canonical[key]
            found = (target, default_locale if target in {"title", "body"} else None)
        elif (
            found is None
            and "." in field.label
            and normalized(field.label.rsplit(".", 1)[-1]) in canonical
        ):
            target = canonical[normalized(field.label.rsplit(".", 1)[-1])]
            found = (target, default_locale if target in {"title", "body"} else None)
        if found:
            target, locale = found
            result.setdefault(
                (target, locale), ImportFieldMapping(target, field.id, locale=locale)
            )
            if key in {"availability", "quantityinstock"}:
                result[(target, locale)] = ImportFieldMapping(
                    target, field.id, locale=locale
                )
            if key in {"вагакг", "вескг"}:
                result[("weight_unit", None)] = ImportFieldMapping(
                    "weight_unit", constant="kg"
                )
            if key.endswith("см") and target in {"length", "width", "height"}:
                result[(target + "_unit", None)] = ImportFieldMapping(
                    target + "_unit", constant="cm"
                )
    if old_price:
        result[("regular_price", None)] = ImportFieldMapping("regular_price", old_price)
        if price:
            result[("sale_price", None)] = ImportFieldMapping("sale_price", price)
            result.pop(("discount", None), None)
    return tuple(result.values())
