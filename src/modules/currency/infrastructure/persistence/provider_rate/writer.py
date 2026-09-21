from datetime import datetime, date
from typing import Sequence
from uuid import uuid4
import hashlib
import sqlalchemy as sa
from src.modules.currency.application.provider.dto.provider_rate_dto import (
    ProviderRateDTO,
)
from src.modules.currency.domain.provider.error import ProviderRateInvalid
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.infrastructure.persistence.directory.model import (
    CurrencyModel,
)
from src.modules.currency.infrastructure.persistence.provider_rate.model import (
    ProviderRateModel,
)


class GlobalProviderRateWriter:
    """Publish immutable provider revisions with semantic idempotency."""

    def __init__(self, session):
        self.session = session

    async def save_many(
        self, *, provider: ProviderCode, rates: Sequence[ProviderRateDTO], now: datetime
    ) -> tuple[int, int]:
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


__all__ = ["GlobalProviderRateWriter"]
