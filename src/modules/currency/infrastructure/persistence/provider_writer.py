from contextlib import asynccontextmanager
import hashlib
from uuid import uuid4

import sqlalchemy as sa

from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork
from src.modules.currency.domain.errors import ProviderRateInvalid
from .models import ProviderRateModel, RateImportModel, CurrencyModel


class GlobalProviderRateWriter:
    def __init__(self, session):
        self.session = session

    async def start(self, identifier, provider, start_date, end_date, now):
        await self.session.execute(
            sa.insert(RateImportModel.__table__).values(
                id=identifier,
                provider_code=str(provider),
                started_at=now,
                requested_date_from=start_date,
                requested_date_to=end_date,
                status="running",
                received_count=0,
                created_count=0,
                updated_count=0,
                error_count=0,
            )
        )

    async def finish(
        self, identifier, *, status, now, received=0, created=0, updated=0, error=None
    ):
        table = RateImportModel.__table__
        await self.session.execute(
            sa.update(table)
            .where(table.c.id == identifier)
            .values(
                status=status,
                finished_at=now,
                received_count=received,
                created_count=created,
                updated_count=updated,
                error_count=int(error is not None),
                error_message=error,
            )
        )

    async def save_many(self, *, provider, rates, now):
        identities = [(r.pair, r.effective_date) for r in rates]
        if len(set(identities)) != len(identities):
            raise ProviderRateInvalid(
                "Provider returned duplicate currency/date pairs."
            )
        # One provider publication at a time. Readers retain their committed view.
        key = int.from_bytes(
            hashlib.sha256(f"fx-provider:{provider}".encode()).digest()[:8],
            "big",
            signed=True,
        )
        await self.session.execute(
            sa.text("SELECT pg_advisory_xact_lock(:key)"), {"key": key}
        )
        codes = set(
            (
                await self.session.execute(sa.select(CurrencyModel.__table__.c.code))
            ).scalars()
        )
        if any(
            str(r.pair.source) not in codes or str(r.pair.target) not in codes
            for r in rates
        ):
            raise ProviderRateInvalid(
                "Provider returned a currency absent from the directory."
            )
        table = ProviderRateModel.__table__
        earliest, latest = min(r.effective_date for r in rates), max(
            r.effective_date for r in rates
        )
        previous = (
            await self.session.execute(
                sa.select(table).where(
                    table.c.provider_code == str(provider),
                    table.c.is_current,
                    table.c.effective_date.between(earliest, latest),
                )
            )
        ).mappings()
        current = {
            (r["source_currency"], r["target_currency"], r["effective_date"]): r
            for r in previous
        }
        inserts, superseded = [], []
        created = updated = 0
        for rate in sorted(
            rates,
            key=lambda r: (str(r.pair.source), str(r.pair.target), r.effective_date),
        ):
            identity = (
                str(rate.pair.source),
                str(rate.pair.target),
                rate.effective_date,
            )
            old = current.get(identity)
            # Semantic equality, independent of payload ordering and fetch time.
            if (
                old
                and old["rate"] == rate.rate
                and old["calculated_date"] == rate.calculated_date
            ):
                continue
            if old:
                updated += 1
                superseded.append(old["id"])
            else:
                created += 1
            value = format(rate.rate, "f")
            value = value.rstrip("0").rstrip(".") if "." in value else value
            digest = hashlib.sha256(
                f"{provider}:{identity}:{value}:{rate.calculated_date}".encode()
            ).hexdigest()
            inserts.append(
                dict(
                    id=uuid4(),
                    provider_code=str(provider),
                    source_currency=identity[0],
                    target_currency=identity[1],
                    rate=rate.rate,
                    effective_date=rate.effective_date,
                    revision=old["revision"] + 1 if old else 1,
                    is_current=True,
                    calculated_date=rate.calculated_date,
                    published_at=rate.published_at,
                    fetched_at=now,
                    created_at=now,
                    payload_hash=digest,
                )
            )
        for start in range(0, len(superseded), 1000):
            await self.session.execute(
                sa.update(table)
                .where(table.c.id.in_(superseded[start : start + 1000]))
                .values(is_current=False)
            )
        for start in range(0, len(inserts), 1000):
            await self.session.execute(sa.insert(table), inserts[start : start + 1000])
        return created, updated


class ProviderImportTransactions:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    @asynccontextmanager
    async def __call__(self):
        async with UnitOfWork(self.session_factory) as uow:
            yield GlobalProviderRateWriter(uow.session)
