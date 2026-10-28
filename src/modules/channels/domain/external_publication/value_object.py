"""Конкретный нормализованный снимок публикации без моделей платформ."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)


class PublicationKind(StrEnum):
    """Роли публикаций, поддержанные первым срезом."""

    SIMPLE = "simple"
    VARIABLE = "variable"
    VARIANT = "variant"


@dataclass(frozen=True, slots=True)
class PublicationTitle:
    """Название, действительно полученное для конкретного языка."""

    locale: str
    title: str | None

    def __post_init__(self) -> None:
        """Не допускает подмены неизвестного перевода произвольным объектом."""
        if (
            not isinstance(self.locale, str)
            or self.locale not in {"uk", "ru", "en"}
            or (self.title is not None and not isinstance(self.title, str))
        ):
            raise InvalidExternalPublicationError("Некорректный перевод публикации.")


@dataclass(frozen=True, slots=True)
class PublicationData:
    """Хранит поддержанные общие данные, сохраняя неизвестное значение как None."""

    titles: tuple[PublicationTitle, ...]
    currency: str
    sku: str | None = None
    url: str | None = None
    main_image_url: str | None = None
    price: Decimal | None = None
    regular_price: Decimal | None = None
    sale_price: Decimal | None = None
    quantity: Decimal | None = None
    stock_mode: str = "unknown"
    availability: str | None = None
    status: str | None = None
    inherit_title: bool = False

    def __post_init__(self) -> None:
        """Проверяет числовые значения, языки и известные режимы остатка."""
        if (
            not isinstance(self.titles, tuple)
            or not all(isinstance(item, PublicationTitle) for item in self.titles)
            or len({item.locale for item in self.titles}) != len(self.titles)
            or not isinstance(self.currency, str)
            or self.currency not in {"UAH", "USD", "EUR"}
            or not isinstance(self.stock_mode, str)
            or self.stock_mode
            not in {"own", "parent", "untracked", "unknown", "not_applicable"}
            or type(self.inherit_title) is not bool
            or any(
                value is not None and not isinstance(value, str)
                for value in (
                    self.sku,
                    self.url,
                    self.main_image_url,
                    self.availability,
                    self.status,
                )
            )
            or any(
                value is not None
                and (not isinstance(value, Decimal) or not value.is_finite())
                for value in (
                    self.price,
                    self.regular_price,
                    self.sale_price,
                    self.quantity,
                )
            )
            or any(
                value is not None and value < 0
                for value in (self.price, self.regular_price, self.sale_price)
            )
        ):
            raise InvalidExternalPublicationError("Некорректные данные публикации.")
        # JSONB не сохраняет порядок ключей переводов; порядок не является изменением контента.
        order = {"uk": 0, "ru": 1, "en": 2}
        object.__setattr__(
            self,
            "titles",
            tuple(sorted(self.titles, key=lambda item: order[item.locale])),
        )

    def to_document(self) -> JsonObject:
        """Сериализует Decimal строками без потери точности."""
        return {
            "titles": {item.locale: item.title for item in self.titles},
            "currency": self.currency,
            "sku": self.sku,
            "url": self.url,
            "main_image_url": self.main_image_url,
            "price": str(self.price) if self.price is not None else None,
            "regular_price": (
                str(self.regular_price) if self.regular_price is not None else None
            ),
            "sale_price": str(self.sale_price) if self.sale_price is not None else None,
            "quantity": str(self.quantity) if self.quantity is not None else None,
            "stock_mode": self.stock_mode,
            "availability": self.availability,
            "status": self.status,
            "inherit_title": self.inherit_title,
        }

    @classmethod
    def from_document(cls, document: JsonObject) -> "PublicationData":
        """Восстанавливает конкретный VO из документа первой версии."""
        try:
            titles = document["titles"]
            if not isinstance(titles, dict):
                raise InvalidExternalPublicationError("Некорректные переводы.")
            return cls(
                titles=tuple(
                    PublicationTitle(locale, title) for locale, title in titles.items()
                ),
                currency=document["currency"],
                sku=document.get("sku"),
                url=document.get("url"),
                main_image_url=document.get("main_image_url"),
                price=decimal_value(document.get("price")),
                regular_price=decimal_value(document.get("regular_price")),
                sale_price=decimal_value(document.get("sale_price")),
                quantity=decimal_value(document.get("quantity")),
                stock_mode=document.get("stock_mode", "unknown"),
                availability=document.get("availability"),
                status=document.get("status"),
                inherit_title=document.get("inherit_title", False),
            )
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise InvalidExternalPublicationError(
                "Неподдерживаемый документ публикации."
            ) from None


def decimal_value(value: str | int | float | None) -> Decimal | None:
    """Различает неизвестное число и ноль, отклоняя bool и нечисловые значения."""
    if value is None or value == "":
        return None
    if type(value) not in {str, int, float}:
        raise InvalidExternalPublicationError("Некорректное числовое значение.")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise InvalidExternalPublicationError(
            "Некорректное числовое значение."
        ) from None
    if not number.is_finite():
        raise InvalidExternalPublicationError("Нечисловое значение публикации.")
    return number
