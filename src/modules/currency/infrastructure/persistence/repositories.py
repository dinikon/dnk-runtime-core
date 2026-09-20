from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from uuid import uuid4
import hashlib

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS
from src.modules.currency.domain.models import (
    CurrencyInfo,
    CurrencyPolicy,
    CurrencyPair,
    ProviderCode,
    RateDatePolicy,
    RoundingMode,
    RateRecord,
    FunctionalCurrencyPeriod,
)
from src.modules.currency.domain.errors import (
    CurrencyNotFound,
    CurrencyPolicyNotConfigured,
    CurrencyConflict,
    FunctionalCurrencyNotConfigured,
)
from .models import (
    CurrencyModel,
    CurrencyPolicyModel,
    EnabledCurrencyModel,
    FunctionalCurrencyPeriodModel,
    ManualExchangeRateModel,
    ProviderRateModel,
    RateImportModel,
)


def rate_record(row, provider):
    return RateRecord(
        EntityIdVO.from_value(row["id"]),
        CurrencyPair(Code(row["source_currency"]), Code(row["target_currency"])),
        row["rate"],
        row["effective_date"],
        provider,
        row["revision"],
        row["is_current"],
        row.get("calculated_date"),
    )


class ScopedRepository:
    def __init__(self, session, naming):
        self.session, self.naming = session, naming

    def scoped(self, statement, tenant_id):
        return statement.execution_options(
            schema_translate_map={
                TENANT_SCHEMA_ALIAS: self.naming.schema_name(tenant_id)
            }
        )

    async def advisory(self, key):
        digest = int.from_bytes(
            hashlib.sha256(key.encode()).digest()[:8], "big", signed=True
        )
        await self.session.execute(
            sa.text("SELECT pg_advisory_xact_lock(:key)"), {"key": digest}
        )


class SqlCurrencyDirectory:
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

    async def get(self, code):
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

    async def exists(self, code):
        return await self.session.scalar(
            sa.select(sa.exists().where(CurrencyModel.__table__.c.code == str(code)))
        )

    async def list_active(self):
        table = CurrencyModel.__table__
        rows = (
            await self.session.execute(
                sa.select(table).where(table.c.is_active).order_by(table.c.code)
            )
        ).mappings()
        return [self.info(row) for row in rows]


class SqlCurrencyPolicyRepository(ScopedRepository):
    async def lock(self, *, tenant_id):
        await self.advisory(f"currency-policy:{tenant_id}")

    async def get(self, *, tenant_id):
        table = CurrencyPolicyModel.__table__
        row = (
            (
                await self.session.execute(
                    self.scoped(sa.select(table).where(table.c.id == 1), tenant_id)
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise CurrencyPolicyNotConfigured(
                "Configure the organization's currency policy first."
            )
        return CurrencyPolicy(
            Code(row["default_transaction_currency"]),
            ProviderCode(row["provider_code"]),
            RateDatePolicy(row["rate_date_policy"]),
            RoundingMode(row["rounding_mode"]),
            row["allow_cross_rate"],
            Code(row["bridge_currency"]),
            row["business_timezone"],
            row["version"],
        )

    async def save(self, *, tenant_id, policy, expected_version, now):
        table = CurrencyPolicyModel.__table__
        values = dict(
            default_transaction_currency=str(policy.default_transaction_currency),
            provider_code=str(policy.provider_code),
            rate_date_policy=policy.rate_date_policy.value,
            rounding_mode=policy.rounding_mode.value,
            allow_cross_rate=policy.allow_cross_rate,
            bridge_currency=str(policy.bridge_currency),
            business_timezone=policy.business_timezone,
            version=policy.version,
            updated_at=now,
        )
        if expected_version == 0:
            result = await self.session.execute(
                self.scoped(
                    pg_insert(table)
                    .values(id=1, created_at=now, **values)
                    .on_conflict_do_nothing()
                    .returning(table.c.id),
                    tenant_id,
                )
            )
        else:
            result = await self.session.execute(
                self.scoped(
                    sa.update(table)
                    .where(table.c.id == 1, table.c.version == expected_version)
                    .values(**values)
                    .returning(table.c.id),
                    tenant_id,
                )
            )
        if result.scalar_one_or_none() is None:
            raise CurrencyConflict("Currency settings changed. Reload before saving.")

    async def enabled(self, *, tenant_id):
        table = EnabledCurrencyModel.__table__
        return {
            Code(code)
            for code in (
                await self.session.execute(
                    self.scoped(
                        sa.select(table.c.currency_code).where(table.c.enabled),
                        tenant_id,
                    )
                )
            ).scalars()
        }

    async def set_enabled(self, *, tenant_id, code, enabled, now):
        table = EnabledCurrencyModel.__table__
        statement = pg_insert(table).values(
            currency_code=str(code), enabled=enabled, created_at=now, updated_at=now
        )
        await self.session.execute(
            self.scoped(
                statement.on_conflict_do_update(
                    index_elements=[table.c.currency_code],
                    set_=dict(enabled=enabled, updated_at=now),
                ),
                tenant_id,
            )
        )


class SqlFunctionalCurrencyRepository(ScopedRepository):
    @staticmethod
    def period(row):
        return FunctionalCurrencyPeriod(
            EntityIdVO.from_value(row["id"]),
            Code(row["currency_code"]),
            row["valid_from"],
            row["valid_to"],
            row["created_at"],
            EntityIdVO.from_value(row["created_by"]),
            row["reason"],
        )

    async def get_for_date(self, *, tenant_id, business_date):
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

    async def list_periods(self, *, tenant_id):
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

    async def add(self, *, tenant_id, period):
        values = {
            "id": period.id.uuid,
            "valid_from": period.valid_from,
            "valid_to": period.valid_to,
            "created_at": period.created_at,
            "created_by": period.created_by.uuid,
            "reason": period.reason,
        }
        values["currency_code"] = str(period.currency)
        await self.session.execute(
            self.scoped(
                sa.insert(FunctionalCurrencyPeriodModel.__table__).values(**values),
                tenant_id,
            )
        )

    async def close(self, *, tenant_id, period_id, valid_to):
        table = FunctionalCurrencyPeriodModel.__table__
        await self.session.execute(
            self.scoped(
                sa.update(table)
                .where(table.c.id == period_id.uuid)
                .values(valid_to=valid_to),
                tenant_id,
            )
        )


class SqlRateRepository(ScopedRepository):
    @staticmethod
    def table(provider):
        if str(provider) == "MANUAL":
            return ManualExchangeRateModel.__table__
        return ProviderRateModel.__table__

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

    async def find(self, *, tenant_id, provider, pair, requested_date, policy):
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
        self, *, tenant_id, provider, pair, bridge, requested_date, policy
    ):
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

    async def set_manual(self, *, tenant_id, pair, rate, effective_date, actor_id, now):
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
            return rate_record(previous, ProviderCode("MANUAL"))
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
            id=uuid4(),
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
        return rate_record(values, ProviderCode("MANUAL"))

    async def history(self, *, tenant_id, provider, pair=None, limit=100, offset=0):
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

    async def provider_status(self, provider):
        imports, rates = RateImportModel.__table__, ProviderRateModel.__table__
        last = (
            (
                await self.session.execute(
                    sa.select(imports)
                    .where(imports.c.provider_code == str(provider))
                    .order_by(imports.c.started_at.desc(), imports.c.id.desc())
                    .limit(1)
                )
            )
            .mappings()
            .first()
        )
        latest = await self.session.scalar(
            sa.select(sa.func.max(rates.c.effective_date)).where(
                rates.c.provider_code == str(provider), rates.c.is_current
            )
        )
        return {
            "last_import": dict(last) if last else None,
            "last_available_rate_date": latest,
        }
