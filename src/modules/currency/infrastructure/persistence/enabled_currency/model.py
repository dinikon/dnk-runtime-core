from __future__ import annotations
import sqlalchemy as sa
from src.modules.currency.infrastructure.persistence.schema import code_check
from src.modules.currency.infrastructure.persistence.schema import timestamps
from src.modules.shared.infrastructure.persistence import TenantBase


class EnabledCurrencyModel(TenantBase):
    """Persistence mapping for enabled currency."""

    __table__ = sa.Table(
        "enabled_currency",
        TenantBase.metadata,
        sa.Column("currency_code", sa.String(3), primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False),
        *timestamps(),
        code_check("currency_code", "ck_enabled_currency_code"),
    )


__all__ = ["EnabledCurrencyModel"]
