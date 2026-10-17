import json
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit
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


def text(value: Any) -> str | None:
    """Возвращает непустую строку без выдумывания отсутствующих данных."""
    return value if isinstance(value, str) and value.strip() else None


def safe_url(value: Any) -> str | None:
    """Разрешает только обычные ссылки HTTP(S) без встроенных credentials."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        return (
            value
            if parsed.scheme in ("https", "http")
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            else None
        )
    except ValueError:
        return None


def number(value: Any) -> Decimal | None:
    """Сохраняет точность десятичных значений, отличая ноль от отсутствия."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def objects(value: Any) -> list[dict[str, Any]]:
    """Возвращает только объектные элементы необязательной коллекции."""
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def prom_sale_price(price: Decimal | None, discount: Any) -> Decimal | None:
    """Преобразует заданную скидку Prom в цену без оценки периода её активности."""
    if price is None or price < 0 or not isinstance(discount, dict):
        return None
    value = number(discount.get("value"))
    if value is None or value < 0:
        return None
    if discount.get("type") == "percent" and value <= 100:
        return price * (Decimal(100) - value) / Decimal(100)
    if discount.get("type") == "amount" and value <= price:
        return price - value
    return None


class PublicationNormalizer:
    """Переводит native JSON платформы в типизированные поля Read документа."""

    def __init__(self, sanitizer: PublicationHtmlSanitizerPort) -> None:
        """Принимает порт очистки HTML отдельно от правил платформ."""
        self._sanitizer = sanitizer

    def normalize(
        self,
        kind: str,
        raw: dict[str, Any],
        *,
        currency: str | None = None,
        parent_id: str | None = None,
    ) -> PublicationSourceResource:
        """Сохраняет неизвестные native поля и нормализует поддержанные поля карточки."""
        if kind not in ("prom", "woocommerce"):
            raise PublicationSourceError("unsupported_platform")
        external_id = raw.get("id")
        if type(external_id) is not int or external_id <= 0:
            raise PublicationSourceError("invalid_source_data")
        woo = kind == "woocommerce"
        images = objects(raw.get("images"))
        image_values = [
            PublicationImageVO(
                url, text(item.get("alt")) or text(item.get("name")) or ""
            )
            for item in images
            if (url := safe_url(item.get("src") if woo else item.get("url")))
        ]
        main = (
            safe_url(raw.get("main_image"))
            if not woo
            else (
                safe_url((raw.get("image") or {}).get("src"))
                if isinstance(raw.get("image"), dict)
                else None
            )
        )
        if main and main not in [image.url for image in image_values]:
            image_values.insert(0, PublicationImageVO(main, ""))
        categories = (
            objects(raw.get("categories"))
            if woo
            else [
                value
                for key in ("group", "category")
                if isinstance(value := raw.get(key), dict)
            ]
        )
        category_values = tuple(
            PublicationCategoryVO(
                str(value.get("id", "")), text(value.get("name")) or ""
            )
            for value in categories
        )
        attrs = (
            objects(raw.get("attributes"))
            if woo
            else objects(raw.get("attributes")) + objects(raw.get("params"))
        )
        attr_values = []
        for item in attrs:
            name = text(item.get("name"))
            value = item.get("option", item.get("value"))
            if isinstance(item.get("options"), list):
                value = ", ".join(
                    str(option)
                    for option in item["options"]
                    if isinstance(option, (str, int, float))
                )
            if (
                name
                and value is not None
                and isinstance(value, (str, int, float, bool))
            ):
                attr_values.append(
                    PublicationAttributeVO(name, str(value), text(item.get("unit")))
                )
        variations = raw.get("variations")
        expected = len(variations) if woo and isinstance(variations, list) else None
        if not woo:
            base = raw.get("variation_base_id")
            if (
                raw.get("is_variation") is True
                and type(base) is int
                and base > 0
                and base != external_id
            ):
                parent_id = str(base)
        source_currency = currency if woo else text(raw.get("currency"))
        warnings = []
        if text(raw.get("name")) is None:
            warnings.append("title_unavailable")
        if source_currency is None:
            warnings.append("currency_unavailable")
        price = number(raw.get("price"))
        if raw.get("price") not in (None, "") and price is None:
            warnings.append("invalid_price")
        regular_price = number(raw.get("regular_price")) if woo else price
        sale_price = (
            number(raw.get("sale_price"))
            if woo
            else prom_sale_price(price, raw.get("discount"))
        )
        if not woo and raw.get("discount") not in (None, {}) and sale_price is None:
            warnings.append("invalid_discount")
        description, short = text(raw.get("description")), text(
            raw.get("short_description")
        )
        document = PublicationReadDocumentVO(
            title=text(raw.get("name")),
            sku=text(raw.get("sku")),
            external_url=safe_url(raw.get("permalink") if woo else raw.get("url")),
            description_html=(
                self._sanitizer.clean(description) if description else None
            ),
            short_description_html=self._sanitizer.clean(short) if short else None,
            price=price,
            regular_price=regular_price,
            sale_price=sale_price,
            currency=source_currency,
            quantity=number(
                raw.get("stock_quantity") if woo else raw.get("quantity_in_stock")
            ),
            availability=text(raw.get("stock_status") if woo else raw.get("presence")),
            source_status=text(raw.get("status")),
            product_type=text(raw.get("type") if woo else raw.get("selling_type")),
            images=tuple(image_values),
            categories=category_values,
            attributes=tuple(attr_values),
            expected_variations=expected,
            warnings=tuple(warnings),
        )
        return PublicationSourceResource(
            "variation" if woo and parent_id is not None else "product",
            str(external_id),
            parent_id,
            json.dumps(raw, ensure_ascii=False, sort_keys=True),
            document,
        )
