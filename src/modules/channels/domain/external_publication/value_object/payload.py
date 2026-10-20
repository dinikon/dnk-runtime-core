from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Self
from src.modules.channels.domain.error import ChannelsValidationError
from src.modules.channels.domain.external_publication.value_object.core import (
    JsonValue,
    PublicationCoreVO,
    validate_observed_values,
)


def decimal_text(value: Decimal | None) -> str | None:
    """Сериализует Decimal без потери точности и незначащего масштаба."""
    if value is None:
        return None
    result = format(value, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if result in ("-0", "") else result


@dataclass(frozen=True, slots=True)
class PublicationPromotionVO:
    """Хранит границы акции с явной точностью и временной зоной источника."""

    starts_at: str | None
    ends_at: str | None
    timezone: str
    precision: str

    def __post_init__(self) -> None:
        """Отклоняет неоднозначную или некорректную нормализованную дату."""
        if (
            self.precision not in ("day", "instant")
            or not isinstance(self.timezone, str)
            or not self.timezone
        ):
            raise ChannelsValidationError("invalid_publication_promotion")
        try:
            for value in (self.starts_at, self.ends_at):
                if value is not None:
                    parsed = datetime.fromisoformat(value)
                    if self.precision == "day" and len(value) != 10:
                        raise ValueError("invalid_day")
                    if self.precision == "instant" and parsed.utcoffset() is None:
                        raise ValueError("missing_timezone")
        except (ValueError, TypeError):
            raise ChannelsValidationError("invalid_publication_promotion") from None

    def to_document(self) -> dict[str, JsonValue]:
        """Возвращает независимое JSON-представление периода."""
        return {
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "timezone": self.timezone,
            "precision": self.precision,
        }


@dataclass(frozen=True, slots=True)
class PublicationPayloadVO:
    """Хранит типизированный снимок списка; не является товаром Catalog."""

    sku: str | None
    titles: tuple[tuple[str, str], ...]
    display_locale: str | None
    price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    stock_status: str
    main_image_url: str | None
    promotion: PublicationPromotionVO | None = None

    def __post_init__(self) -> None:
        """Проверяет значения снимка и исключает повторяющиеся локали."""
        if not isinstance(self.titles, tuple) or any(
            not isinstance(pair, tuple) or len(pair) != 2 for pair in self.titles
        ):
            raise ChannelsValidationError("invalid_publication_titles")
        if len(dict(self.titles)) != len(self.titles) or any(
            not isinstance(locale, str) or not locale or not isinstance(title, str)
            for locale, title in self.titles
        ):
            raise ChannelsValidationError("invalid_publication_titles")
        if self.display_locale is not None and not isinstance(self.display_locale, str):
            raise ChannelsValidationError("invalid_publication_locale")
        for value in (self.sku, self.currency, self.main_image_url):
            if value is not None and not isinstance(value, str):
                raise ChannelsValidationError("invalid_publication_payload")
        validate_observed_values(
            self.price, self.sale_price, self.quantity, self.stock_status
        )

    @property
    def title(self) -> str | None:
        """Читает только явно выбранную локаль без fallback на другой язык."""
        return dict(self.titles).get(self.display_locale or "und")

    @classmethod
    def from_core(
        cls,
        core: PublicationCoreVO,
        *,
        titles: tuple[tuple[str, str], ...] | None = None,
        promotion: PublicationPromotionVO | None = None,
    ) -> Self:
        """Строит снимок из типизированной нормализации плагина."""
        return cls(
            core.external_sku,
            (
                titles
                if titles is not None
                else (
                    ((core.title_locale or "und", core.title),)
                    if core.title is not None
                    else ()
                )
            ),
            core.title_locale,
            core.price,
            core.sale_price,
            core.currency,
            core.quantity,
            core.stock_status,
            core.main_image_url,
            promotion,
        )

    def to_core(
        self,
        resource_type: str,
        external_id: str,
        source_updated_at: datetime | None,
        warnings: tuple[str, ...],
    ) -> PublicationCoreVO:
        """Строит временную проекцию для действующих сценариев чтения и Draft."""
        return PublicationCoreVO(
            resource_type,
            external_id,
            self.sku,
            self.price,
            self.sale_price,
            self.currency,
            self.quantity,
            self.stock_status,
            self.title,
            self.display_locale,
            self.main_image_url,
            source_updated_at,
            warnings,
        )

    def to_document(self) -> dict[str, JsonValue]:
        """Возвращает версионированный JSON со строковыми денежными величинами."""
        return {
            "schema_version": 1,
            "sku": self.sku,
            "titles": dict(self.titles),
            "display_locale": self.display_locale,
            "pricing": {
                "regular": decimal_text(self.price),
                "sale": decimal_text(self.sale_price),
                "currency": self.currency,
                "promotion": self.promotion.to_document() if self.promotion else None,
            },
            "stock": {
                "quantity": decimal_text(self.quantity),
                "status": self.stock_status,
            },
            "main_image": (
                {"url": self.main_image_url}
                if self.main_image_url is not None
                else None
            ),
        }

    @classmethod
    def from_document(cls, document: dict[str, JsonValue]) -> Self:
        """Читает известную версию, отклоняя повреждённый сохранённый снимок."""
        try:
            if (
                type(document["schema_version"]) is not int
                or document["schema_version"] != 1
            ):
                raise ValueError("unsupported_version")
            pricing, stock = document["pricing"], document["stock"]
            if not isinstance(pricing, dict) or not isinstance(stock, dict):
                raise ValueError("invalid_structure")
            if any(
                value is not None and not isinstance(value, str)
                for value in (pricing["regular"], pricing["sale"], stock["quantity"])
            ):
                raise ValueError("decimal_string_required")
            promotion, image = pricing["promotion"], document["main_image"]
            return cls(
                document["sku"],
                tuple(sorted(document["titles"].items())),
                document["display_locale"],
                Decimal(pricing["regular"]) if pricing["regular"] is not None else None,
                Decimal(pricing["sale"]) if pricing["sale"] is not None else None,
                pricing["currency"],
                Decimal(stock["quantity"]) if stock["quantity"] is not None else None,
                stock["status"],
                image["url"] if image is not None else None,
                PublicationPromotionVO(**promotion) if promotion is not None else None,
            )
        except (KeyError, TypeError, ValueError, ArithmeticError, AttributeError):
            raise ChannelsValidationError("invalid_publication_payload") from None
