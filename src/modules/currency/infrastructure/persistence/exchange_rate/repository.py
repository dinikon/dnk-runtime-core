from __future__ import annotations
from datetime import date
from typing import Sequence
import sqlalchemy as sa
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.exchange_rate.value_object.rate_record import (
    RateRecord,
)
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.infrastructure.persistence.exchange_rate.mapper import (
    rate_record,
)
from src.modules.currency.infrastructure.persistence.scoped_repository import (
    ScopedRepository,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlRateReader(ScopedRepository):
    """Common local SQL lookup algorithm for a concrete rate store."""

    @staticmethod
    def table(provider):
        raise NotImplementedError

    @staticmethod
    def pair_filter(table, pair):
        return sa.and_(
            table.c.source_currency == str(pair.source),
            table.c.target_currency == str(pair.target),
        )

    def current_filter(self, table, provider, requested_date, policy):
        clauses = [
            table.c.is_current,
            (
                table.c.effective_date == requested_date
                if policy == RateDatePolicy.EXACT
                else table.c.effective_date <= requested_date
            ),
        ]
        if "provider_code" in table.c:
            clauses.append(table.c.provider_code == str(provider))
        return clauses

    async def find(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair,
        requested_date: date,
        policy: RateDatePolicy,
    ) -> RateRecord | None:
        table = self.table(provider)
        query = (
            sa.select(table)
            .where(
                self.pair_filter(table, pair),
                *self.current_filter(table, provider, requested_date, policy),
            )
            .order_by(table.c.effective_date.desc())
            .limit(1)
        )
        row = (
            (await self.session.execute(self.scoped(query, tenant_id)))
            .mappings()
            .first()
        )
        return rate_record(row, provider) if row else None

    async def find_cross(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair,
        bridge: CurrencyCodeVO,
        requested_date: date,
        policy: RateDatePolicy,
    ) -> tuple[RateRecord, RateRecord] | None:
        table = self.table(provider)
        legs = []
        for start, end in ((pair.source, bridge), (bridge, pair.target)):
            forward = CurrencyPair(start, end)
            legs.append(
                sa.select(table)
                .where(
                    sa.or_(
                        self.pair_filter(table, forward),
                        self.pair_filter(table, forward.inverse()),
                    ),
                    *self.current_filter(table, provider, requested_date, policy),
                )
                .subquery()
            )
        a, b = legs
        # Latest common date; prefer direct orientation on ties, deterministically.
        query = (
            sa.select(a.c.id, b.c.id.label("second_id"))
            .join(b, a.c.effective_date == b.c.effective_date)
            .order_by(
                a.c.effective_date.desc(),
                (a.c.source_currency == str(pair.source)).desc(),
                (b.c.source_currency == str(bridge)).desc(),
            )
            .limit(1)
        )
        ids = (await self.session.execute(self.scoped(query, tenant_id))).first()
        if ids is None:
            return None
        rows = (
            await self.session.execute(
                self.scoped(sa.select(table).where(table.c.id.in_(ids)), tenant_id)
            )
        ).mappings()
        records = {row["id"]: rate_record(row, provider) for row in rows}
        return records[ids[0]], records[ids[1]]

    async def history(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair | None,
        limit: int,
        offset: int,
    ) -> Sequence[RateRecord]:
        table = self.table(provider)
        query = sa.select(table)
        if "provider_code" in table.c:
            query = query.where(table.c.provider_code == str(provider))
        if pair:
            query = query.where(self.pair_filter(table, pair))
        query = (
            query.order_by(
                table.c.effective_date.desc(),
                table.c.source_currency,
                table.c.target_currency,
                table.c.revision.desc(),
            )
            .limit(min(limit, 500))
            .offset(offset)
        )
        return [
            rate_record(row, provider)
            for row in (
                await self.session.execute(self.scoped(query, tenant_id))
            ).mappings()
        ]


__all__ = ["SqlRateReader"]
