"""Контракт скидок Prom, точность вычислений и границы календарных дат."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
import unittest
from unittest.mock import AsyncMock
from src.modules.channels.application.plugin_contract import (
    ConnectionCredentialsDTO,
    HttpResultDTO,
    ProviderJsonValue,
    ReadPublicationPageInputDTO,
    ResourceSettingsDTO,
)
from src.modules.channels.infrastructure.plugin.prom.core_normalizer import (
    normalize_product,
)
from src.modules.channels.infrastructure.plugin.prom.read_publication_page import (
    PromReadPublicationPagePlugin,
)

SETTINGS = ResourceSettingsDTO(
    "https://my.prom.ua", {"locales": list(("ru",)), "currency": "UAH"}
)
DISCOUNT: dict[str, ProviderJsonValue] = {
    "type": "amount",
    "value": 70,
    "date_start": "01.10.2026",
    "date_end": "31.10.2026",
}
PRODUCT: dict[str, ProviderJsonValue] = {
    "id": 99,
    "name": "Товар",
    "price": Decimal("899"),
    "currency": "UAH",
    "quantity_in_stock": 1,
    "presence": "available",
    "discount": DISCOUNT,
}


class PromDiscountTests(unittest.TestCase):
    """Проверяет нормализацию скидок без сети и зависимости от текущего дня."""

    def test_amount_and_percent_match_public_biovit_examples(self) -> None:
        """Оба вида скидок совпадают с публичными карточками Prom Biovit."""
        for kind, price, value, expected in (
            ("amount", "899", "70.0", "829"),
            ("percent", "830", "10", "747"),
            ("percent", "99.99", "10", "89.991"),
            ("percent", "123.45000000001", "10", "111.105000000009"),
            ("amount", "1.000000000001", "0.000000000001", "1"),
            ("amount", "899", "899", "0"),
            ("percent", "830", "100", "0"),
        ):
            with self.subTest(kind=kind, price=price, value=value):
                result = normalize_product(
                    {
                        **PRODUCT,
                        "price": price,
                        "discount": {**DISCOUNT, "type": kind, "value": value},
                    },
                    SETTINGS,
                    observed_on=date(2026, 10, 18),
                )
                self.assertEqual(result.core.price, Decimal(price))
                self.assertEqual(result.core.sale_price, Decimal(expected))
                self.assertEqual(result.core.warnings, ())
                self.assertEqual(result.meta.provider["discount"]["value"], value)

    def test_discount_dates_include_start_and_end_days(self) -> None:
        """Будущая и истёкшая акция не попадают в sale_price; границы включены."""
        for observed_on, expected in (
            (date(2026, 9, 30), None),
            (date(2026, 10, 1), Decimal("829")),
            (date(2026, 10, 31), Decimal("829")),
            (date(2026, 11, 1), None),
        ):
            with self.subTest(observed_on=observed_on):
                result = normalize_product(PRODUCT, SETTINGS, observed_on=observed_on)
                self.assertEqual(result.core.sale_price, expected)
                self.assertEqual(result.core.warnings, ())
                self.assertEqual(
                    result.meta.provider["discount"]["date_end"], "31.10.2026"
                )

    def test_missing_and_zero_discount_are_not_sales(self) -> None:
        """Нет скидки или размер равен нулю: цена не превращается в акционную."""
        for discount in (None, {**DISCOUNT, "value": 0}):
            with self.subTest(discount=discount):
                result = normalize_product(
                    {**PRODUCT, "discount": discount},
                    SETTINGS,
                    observed_on=date(2026, 10, 18),
                )
                self.assertIsNone(result.core.sale_price)
                self.assertEqual(result.core.warnings, ())

    def test_invalid_discount_keeps_product_and_original_price(self) -> None:
        """Неподдержанные типы, значения и даты дают null с предупреждением."""
        invalid: list[object] = [
            True,
            "10%",
            [],
            {},
            {**DISCOUNT, "type": "unknown"},
            {**DISCOUNT, "date_start": None},
            {**DISCOUNT, "date_end": ""},
            {**DISCOUNT, "date_start": "2026-10-01"},
            {**DISCOUNT, "date_start": "1.10.2026"},
            {**DISCOUNT, "date_start": "31.02.2026"},
            {**DISCOUNT, "date_start": "01.11.2026"},
            {**DISCOUNT, "value": 900},
            {**DISCOUNT, "type": "percent", "value": 101},
        ] + [
            {**DISCOUNT, "value": value}
            for value in (
                None,
                "",
                True,
                False,
                "bad",
                "NaN",
                "Infinity",
                -1,
                "1e18",
                "1e-13",
            )
        ]
        for discount in invalid:
            with self.subTest(discount=discount):
                result = normalize_product(
                    {**PRODUCT, "discount": discount},
                    SETTINGS,
                    observed_on=date(2026, 10, 18),
                )
                self.assertIsNone(result.core.sale_price)
                self.assertEqual(result.core.price, Decimal("899"))
                self.assertEqual(result.core.external_id, "99")
                self.assertEqual(result.core.warnings, ("invalid_sale_price",))

    def test_sale_without_valid_price_and_excess_precision_are_not_guessed(
        self,
    ) -> None:
        """Расчёт не восстанавливает базовую цену и не округляет результат под БД."""
        for extra in (
            {"price": None},
            {"price": "NaN"},
            {"price": -1},
            {
                "price": "123.450000000001",
                "discount": {**DISCOUNT, "type": "percent", "value": 10},
            },
        ):
            with self.subTest(extra=extra):
                result = normalize_product(
                    {**PRODUCT, **extra}, SETTINGS, observed_on=date(2026, 10, 18)
                )
                self.assertIsNone(result.core.sale_price)
                self.assertIn("invalid_sale_price", result.core.warnings)


@dataclass
class FixedClock:
    """Передаёт фиксированный aware instant в настоящий read adapter."""

    value: datetime

    def now(self) -> datetime:
        """Возвращает текущую точку проверки границы календарного дня."""
        return self.value


class PromDiscountPageTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет календарь Kyiv и зимний/летний UTC offset в reader."""

    async def test_reader_uses_kyiv_calendar_including_dst_transition(self) -> None:
        """UTC не завершает скидку раньше/позже локальной полуночи Prom."""
        for instant, day, active in (
            ("2026-10-17T20:59:59+00:00", "18.10.2026", False),
            ("2026-10-17T21:00:00+00:00", "18.10.2026", True),
            ("2026-10-18T20:59:59+00:00", "18.10.2026", True),
            ("2026-10-18T21:00:00+00:00", "18.10.2026", False),
            ("2026-10-25T21:59:59+00:00", "25.10.2026", True),
            ("2026-10-25T22:00:00+00:00", "25.10.2026", False),
        ):
            with self.subTest(instant=instant):
                credentials, transport = AsyncMock(), AsyncMock()
                credentials.resolve.return_value = ConnectionCredentialsDTO(
                    {"token": "test"}
                )
                transport.get.return_value = HttpResultDTO(
                    {
                        "products": [
                            {
                                **PRODUCT,
                                "discount": {
                                    **DISCOUNT,
                                    "date_start": day,
                                    "date_end": day,
                                },
                            }
                        ]
                    },
                    {},
                )
                clock = FixedClock(datetime.fromisoformat(instant).astimezone(UTC))
                result = await PromReadPublicationPagePlugin(
                    credentials, transport, clock=clock
                ).execute(
                    ReadPublicationPageInputDTO(
                        SETTINGS,
                        "prom:1",
                        {
                            "version": 1,
                            "stage": "products",
                            "groups": [1],
                            "group_index": 0,
                            "last_id": None,
                        },
                    )
                )
                self.assertEqual(
                    result.publications[0].core.sale_price,
                    Decimal("829") if active else None,
                )
                self.assertEqual(result.publications[0].core.warnings, ())
