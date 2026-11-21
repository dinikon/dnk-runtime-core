"""Проверка активных валют справочника и точности денежных значений в PostgreSQL."""

from decimal import Decimal
import os
import unittest
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_repository import (
    SqlAlchemyCurrencyQueryRepository,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)


class CurrencySliceOnePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет валютный справочник и точное хранение денежных значений."""

    async def asyncSetUp(self) -> None:
        value = os.environ.get("DNK_TEST_DATABASE_URL")
        if not value:
            self.skipTest(
                "DNK_TEST_DATABASE_URL is required for isolated PostgreSQL tests"
            )
        url = make_url(value).set(drivername="postgresql+asyncpg")
        self.name = "dnk_currency_test_" + uuid4().hex
        self.admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
        async with self.admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{self.name}"'))
        self.engine = create_async_engine(url.set(database=self.name))
        self.addAsyncCleanup(self.drop_database)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            await connection.execute(
                text(
                    "INSERT INTO public.ref_currencies (code, numeric_code, name, minor_units, active) "
                    "VALUES ('UAH', '980', 'Hryvnia', 2, true), ('USD', '840', 'Dollar', 2, true), "
                    "('JPY', '392', 'Yen', 0, false)"
                )
            )

    async def drop_database(self) -> None:
        await self.engine.dispose()
        async with self.admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{self.name}"'))
        await self.admin.dispose()

    async def test_validation_uses_only_active_catalog_currency(self) -> None:
        async with UnitOfWork(self.sessions) as uow:
            handler = ValidateCurrencyHandler(
                SqlAlchemyCurrencyQueryRepository(uow.session)
            )
            result = await handler.execute(ValidateCurrencyQuery(" usd "))
            self.assertEqual(
                (result.code, result.numeric_code, result.minor_units),
                ("USD", "840", 2),
            )
            for code in ("JPY", "ZZZ"):
                with (
                    self.subTest(code=code),
                    self.assertRaises(CurrencyCodeNotSupportedError),
                ):
                    await handler.execute(ValidateCurrencyQuery(code))

    async def test_money_decimal_roundtrip(self) -> None:
        """Сохраняет предельную отрицательную сумму без потери Decimal-точности."""
        amount = MoneyVO(Decimal("-999999999999999.9999"), CurrencyVO("USD"))
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TEMP TABLE money_roundtrip (amount NUMERIC(19,4), currency VARCHAR(3))"
                )
            )
            await connection.execute(
                text("INSERT INTO money_roundtrip VALUES (:amount, :currency)"),
                {"amount": amount.amount, "currency": amount.currency.value},
            )
            row = (
                await connection.execute(
                    text("SELECT amount, currency FROM money_roundtrip")
                )
            ).one()
            self.assertEqual(MoneyVO(row.amount, CurrencyVO(row.currency)), amount)
