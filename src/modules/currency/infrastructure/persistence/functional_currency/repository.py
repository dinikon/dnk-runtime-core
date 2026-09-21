from __future__ import annotations
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError
from typing import Sequence
import sqlalchemy as sa
from src.modules.currency.domain.functional_currency.entity import (
    FunctionalCurrencyPeriod,
)
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyNotConfigured,
)
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyPeriodOverlap,
)
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.currency.infrastructure.persistence.functional_currency.model import (
    FunctionalCurrencyPeriodModel,
)
from src.modules.currency.infrastructure.persistence.scoped_repository import (
    ScopedRepository,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlFunctionalCurrencyRepository(ScopedRepository):
    """Persist dated functional periods and their activation markers."""

    @staticmethod
    def period(row):
        return FunctionalCurrencyPeriod(
            FunctionalCurrencyPeriodIdVO.from_value(row["id"]),
            Code(row["currency_code"]),
            row["valid_from"],
            row["valid_to"],
            row["created_at"],
            EntityIdVO.from_value(row["created_by"]),
            row["reason"],
            row["activation_emitted_at"],
        )

    async def get_for_date(
        self, *, tenant_id: EntityIdVO, business_date: date
    ) -> FunctionalCurrencyPeriod:
        table = FunctionalCurrencyPeriodModel.__table__
        row = (
            (
                await self.session.execute(
                    self.scoped(
                        sa.select(table).where(
                            table.c.valid_from <= business_date,
                            sa.or_(
                                table.c.valid_to.is_(None),
                                table.c.valid_to >= business_date,
                            ),
                        ),
                        tenant_id,
                    )
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise FunctionalCurrencyNotConfigured(
                f"No functional currency on {business_date}."
            )
        return self.period(row)

    async def list_periods(
        self, *, tenant_id: EntityIdVO
    ) -> Sequence[FunctionalCurrencyPeriod]:
        table = FunctionalCurrencyPeriodModel.__table__
        return [
            self.period(row)
            for row in (
                await self.session.execute(
                    self.scoped(
                        sa.select(table).order_by(table.c.valid_from), tenant_id
                    )
                )
            ).mappings()
        ]

    async def add(
        self, *, tenant_id: EntityIdVO, period: FunctionalCurrencyPeriod
    ) -> None:
        values = {
            "id": period.id.uuid,
            "valid_from": period.valid_from,
            "valid_to": period.valid_to,
            "created_at": period.created_at,
            "created_by": period.created_by.uuid,
            "reason": period.reason,
        }
        values["currency_code"] = str(period.currency)
        try:
            await self.session.execute(
                self.scoped(
                    sa.insert(FunctionalCurrencyPeriodModel.__table__).values(**values),
                    tenant_id,
                )
            )
        except IntegrityError as exc:
            original = exc.orig.__cause__
            if (
                getattr(original, "constraint_name", None)
                == "ex_functional_currency_period"
            ):
                raise FunctionalCurrencyPeriodOverlap(
                    "Functional currency periods overlap."
                ) from exc
            raise

    async def close(
        self, *, tenant_id: EntityIdVO, period_id: EntityIdVO, valid_to: date
    ) -> None:
        table = FunctionalCurrencyPeriodModel.__table__
        await self.session.execute(
            self.scoped(
                sa.update(table)
                .where(table.c.id == period_id.uuid)
                .values(valid_to=valid_to),
                tenant_id,
            )
        )

    async def get_by_id(
        self, *, tenant_id: EntityIdVO, period_id: EntityIdVO
    ) -> FunctionalCurrencyPeriod:
        table = FunctionalCurrencyPeriodModel.__table__
        row = (
            (
                await self.session.execute(
                    self.scoped(
                        sa.select(table).where(table.c.id == period_id.uuid), tenant_id
                    )
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise FunctionalCurrencyNotConfigured(
                "Functional currency period does not exist."
            )
        return self.period(row)

    async def mark_activated(
        self, *, tenant_id: EntityIdVO, period_id: EntityIdVO, now: datetime
    ) -> bool:
        table = FunctionalCurrencyPeriodModel.__table__
        result = await self.session.execute(
            self.scoped(
                sa.update(table)
                .where(
                    table.c.id == period_id.uuid,
                    table.c.activation_emitted_at.is_(None),
                )
                .values(activation_emitted_at=now)
                .returning(table.c.id),
                tenant_id,
            )
        )
        return result.scalar_one_or_none() is not None


__all__ = ["SqlFunctionalCurrencyRepository"]
