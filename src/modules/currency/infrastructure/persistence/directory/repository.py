from __future__ import annotations
from typing import Sequence
import sqlalchemy as sa
from src.modules.currency.domain.directory.entity import CurrencyInfo
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.infrastructure.persistence.directory.model import (
    CurrencyModel,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code


class SqlCurrencyDirectory:
    """Public sql currency directory contract."""

    def __init__(self, session):
        self.session = session

    @staticmethod
    def info(row):
        return CurrencyInfo(
            Code(row["code"]),
            row["name"],
            row["minor_units"],
            row["numeric_code"],
            row["symbol"],
            row["is_active"],
            row["valid_from"],
            row["valid_to"],
        )

    async def get(self, code: CurrencyCodeVO) -> CurrencyInfo:
        table = CurrencyModel.__table__
        row = (
            (
                await self.session.execute(
                    sa.select(table).where(table.c.code == str(code))
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise CurrencyNotFound(f"Currency {code} does not exist.")
        return self.info(row)

    async def exists(self, code: CurrencyCodeVO) -> bool:
        return await self.session.scalar(
            sa.select(sa.exists().where(CurrencyModel.__table__.c.code == str(code)))
        )

    async def list_active(self) -> Sequence[CurrencyInfo]:
        table = CurrencyModel.__table__
        rows = (
            await self.session.execute(
                sa.select(table).where(table.c.is_active).order_by(table.c.code)
            )
        ).mappings()
        return [self.info(row) for row in rows]


__all__ = ["SqlCurrencyDirectory"]
