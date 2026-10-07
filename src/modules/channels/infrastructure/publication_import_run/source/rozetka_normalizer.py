import json
from decimal import Decimal
from typing import Any
from src.modules.channels.application.external_publication.port.html_sanitizer import (
    PublicationHtmlSanitizerPort,
)
from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourceResource,
)
from src.modules.channels.domain.external_publication.value_object.read_document import (
    PublicationReadDocumentVO,
    PublicationImageVO,
    PublicationCategoryVO,
    PublicationAttributeVO,
)
from src.modules.channels.infrastructure.publication_import_run.source.normalizer import (
    text,
    safe_url,
    number,
    objects,
)


def item_id(row: dict[str, Any]) -> int:
    """Проверяет внутренний ID, который существует и до публикации на площадке."""
    value = row.get("item_id")
    if type(value) is not int or value <= 0:
        raise PublicationSourceError("invalid_source_data")
    return value


def attribute_value(value: Any) -> str | None:
    """Отображает значения характеристики, сохраняя false, ноль и списки подписей."""
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if isinstance(value, (int, float)) and number(value) is None:
        return None
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, list):
        values = [
            attribute_value(row.get("value") if isinstance(row, dict) else row)
            for row in value
        ]
        return ", ".join(part for part in values if part is not None) or None
    return None


def status(raw: dict[str, Any]) -> str | None:
    """Выбирает внутренний статус, оставляя регистрацию и продажи в native данных."""
    code = raw.get("upload_status")
    label = text(raw.get("upload_status_title"))
    if type(code) is int or isinstance(code, str):
        return f"{label} ({code})" if label else f"rozetka_upload:{code}"
    if label:
        return label
    code = raw.get("rz_status")
    return (
        f"rozetka_status:{code}" if type(code) is int or isinstance(code, str) else None
    )


def prices(
    raw: dict[str, Any], warnings: list[str]
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Отражает цену, старую цену и положительную промо-цену без выдуманной валюты."""
    price, old, promo = (
        number(raw.get(key)) for key in ("price", "price_old", "price_promo")
    )
    typed: dict[int, set[Decimal]] = {1: set(), 2: set()}
    for entry in objects(raw.get("prices")):
        kind, value = entry.get("price_type"), number(entry.get("price"))
        if type(kind) is int and kind in typed and value is not None and value >= 0:
            typed[kind].add(value)
    if price is None and len(typed[2]) == 1:
        price = next(iter(typed[2]))
    if old is None and len(typed[1]) == 1:
        old = next(iter(typed[1]))
    if any(len(values) > 1 for values in typed.values()):
        warnings.append("ambiguous_prices")
    if price is not None and price < 0:
        warnings.append("invalid_price")
        price = None
    if raw.get("price") not in (None, "") and number(raw.get("price")) is None:
        warnings.append("invalid_price")
    if any(
        raw.get(key) not in (None, "") and number(raw.get(key)) is None
        for key in ("price_old", "price_promo")
    ):
        warnings.append("invalid_discount")
    if old is not None and old < 0 and "invalid_discount" not in warnings:
        warnings.append("invalid_discount")
    regular, sale = price, None
    if price is not None and old is not None and old > price:
        regular, sale = old, price
    if price is not None and promo is not None and 0 < promo < price:
        sale = promo
    elif promo is not None and (promo < 0 or (price is not None and promo > price)):
        if "invalid_discount" not in warnings:
            warnings.append("invalid_discount")
    return price, regular, sale


class RozetkaPublicationNormalizer:
    """Собирает Read-карточку Rozetka из списка и проверенных деталей одного товара."""

    def __init__(self, sanitizer: PublicationHtmlSanitizerPort) -> None:
        """Принимает существующий порт очистки описаний."""
        self._sanitizer = sanitizer

    def normalize(
        self, listing: dict[str, Any], details: dict[str, Any]
    ) -> PublicationSourceResource:
        """Сохраняет два native фрагмента; детали перекрывают только присутствующие поля."""
        identity = item_id(listing)
        if item_id(details) != identity:
            raise PublicationSourceError("invalid_source_data")
        raw = {**listing, **details}
        warnings: list[str] = []
        title = text(raw.get("name_ua")) or text(raw.get("name"))
        currency = text(raw.get("currency"))
        if title is None:
            warnings.append("title_unavailable")
        if currency is None:
            warnings.append("currency_unavailable")
        price, regular, sale = prices(raw, warnings)
        description = text(raw.get("description_ua")) or text(raw.get("description"))
        short = text(raw.get("docket_ua")) or text(raw.get("docket"))
        image_values: list[PublicationImageVO] = []
        for key in ("photo", "photo_preview"):
            values = raw.get(key)
            values = (
                [values]
                if isinstance(values, str)
                else values if isinstance(values, list) else []
            )
            for value in values:
                url = safe_url(value)
                if url and url not in [image.url for image in image_values]:
                    image_values.append(PublicationImageVO(url, title or ""))
            if image_values:
                break
        categories: list[PublicationCategoryVO] = []
        for key in ("rz_category", "price_category"):
            value = raw.get(key)
            if not isinstance(value, dict):
                continue
            name = text(value.get("title_ua")) or text(value.get("title"))
            identity_value = value.get("id")
            if name:
                category = PublicationCategoryVO(
                    str(identity_value) if identity_value is not None else "", name
                )
                if category not in categories:
                    categories.append(category)
        attributes: list[PublicationAttributeVO] = []
        for value in objects(raw.get("params")):
            name = text(value.get("title")) or text(value.get("rz_title"))
            native_value = value.get("value_ua")
            if native_value is None or native_value == "":
                native_value = value.get("value")
            if native_value is None:
                native_value = value.get("seller_value")
            rendered = attribute_value(native_value)
            if name and rendered is not None:
                attributes.append(
                    PublicationAttributeVO(name, rendered, text(value.get("unit")))
                )
        availability = raw.get("available")
        availability_code = (
            str(availability)
            if type(availability) is int or isinstance(availability, str)
            else None
        )
        document = PublicationReadDocumentVO(
            title=title,
            sku=text(raw.get("article")),
            external_url=safe_url(raw.get("url")),
            description_html=(
                self._sanitizer.clean(description) if description else None
            ),
            short_description_html=self._sanitizer.clean(short) if short else None,
            price=price,
            regular_price=regular,
            sale_price=sale,
            currency=currency,
            quantity=number(raw.get("stock_quantity")),
            availability={"0": "not_available", "1": "available", "2": "deleted"}.get(
                availability_code,
                (
                    f"rozetka_available:{availability_code}"
                    if availability_code is not None
                    else None
                ),
            ),
            source_status=status(raw),
            product_type=None,
            images=tuple(image_values),
            categories=tuple(categories),
            attributes=tuple(attributes),
            expected_variations=None,
            warnings=tuple(warnings),
        )
        return PublicationSourceResource(
            "product",
            str(identity),
            None,
            json.dumps(
                {"list_item": listing, "detail_item": details},
                ensure_ascii=False,
                sort_keys=True,
            ),
            document,
        )
