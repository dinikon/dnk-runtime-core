from __future__ import annotations
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert as pg_insert
import sqlalchemy as sa
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.currency.domain.policy.error import CurrencyConflict
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.currency.domain.policy.value_object.rounding_mode import RoundingMode
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.infrastructure.persistence.policy.model import (
    CurrencyPolicyModel,
)
from src.modules.currency.infrastructure.persistence.scoped_repository import (
    ScopedRepository,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlCurrencyPolicyRepository(ScopedRepository):
    """Explicit persistence contract for currency policy."""

    async def lock(self, *, tenant_id: EntityIdVO) -> None:
        await self.advisory(f"currency-policy:{tenant_id}")

    async def get(self, *, tenant_id: EntityIdVO) -> CurrencyPolicy:
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
            (
                Code(row["default_display_currency"])
                if row["default_display_currency"]
                else None
            ),
        )

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        policy: CurrencyPolicy,
        expected_version: int,
        now: datetime,
    ) -> None:
        table = CurrencyPolicyModel.__table__
        values = dict(
            default_transaction_currency=str(policy.default_transaction_currency),
            provider_code=str(policy.provider_code),
            rate_date_policy=policy.rate_date_policy.value,
            rounding_mode=policy.rounding_mode.value,
            allow_cross_rate=policy.allow_cross_rate,
            bridge_currency=str(policy.bridge_currency),
            business_timezone=policy.business_timezone,
            default_display_currency=(
                str(policy.default_display_currency)
                if policy.default_display_currency
                else None
            ),
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


__all__ = ["SqlCurrencyPolicyRepository"]
