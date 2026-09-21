from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
import sqlalchemy as sa
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.manual_rate.entity import ManualExchangeRate
from src.modules.currency.domain.manual_rate.value_object.id import (
    ManualExchangeRateIdVO,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.infrastructure.persistence.exchange_rate.mapper import (
    rate_record,
)
from src.modules.currency.infrastructure.persistence.exchange_rate.repository import (
    SqlRateReader,
)
from src.modules.currency.infrastructure.persistence.manual_rate.model import (
    ManualExchangeRateModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlManualRateRepository(SqlRateReader):
    """Persistence adapter for manual rate records."""

    @staticmethod
    def table(provider):
        return ManualExchangeRateModel.__table__

    async def set_manual(
        self,
        *,
        identifier: ManualExchangeRateIdVO,
        tenant_id: EntityIdVO,
        pair: CurrencyPair,
        rate: Decimal,
        effective_date: date,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> tuple[ManualExchangeRate, bool]:
        table = ManualExchangeRateModel.__table__
        await self.advisory(
            f"manual-rate:{tenant_id}:{pair.source}:{pair.target}:{effective_date}"
        )
        predicate = sa.and_(
            self.pair_filter(table, pair), table.c.effective_date == effective_date
        )
        previous = (
            (
                await self.session.execute(
                    self.scoped(
                        sa.select(table).where(predicate, table.c.is_current), tenant_id
                    )
                )
            )
            .mappings()
            .first()
        )
        if previous and previous["rate"] == rate:
            return rate_record(previous, ProviderCode("MANUAL")), False
        revision = previous["revision"] + 1 if previous else 1
        await self.session.execute(
            self.scoped(
                sa.update(table)
                .where(predicate, table.c.is_current)
                .values(is_current=False),
                tenant_id,
            )
        )
        values = dict(
            id=identifier.uuid,
            source_currency=str(pair.source),
            target_currency=str(pair.target),
            rate=rate,
            effective_date=effective_date,
            revision=revision,
            is_current=True,
            created_by=actor_id.uuid,
            created_at=now,
        )
        await self.session.execute(
            self.scoped(sa.insert(table).values(**values), tenant_id)
        )
        return rate_record(values, ProviderCode("MANUAL")), True


__all__ = ["SqlManualRateRepository"]
