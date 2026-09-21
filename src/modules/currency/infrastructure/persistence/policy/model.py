from __future__ import annotations
import sqlalchemy as sa
from src.modules.currency.infrastructure.persistence.schema import code_check
from src.modules.currency.infrastructure.persistence.schema import timestamps
from src.modules.shared.infrastructure.persistence import TenantBase


class CurrencyPolicyModel(TenantBase):
    """Persistence mapping for currency policy."""

    __table__ = sa.Table(
        "currency_policy",
        TenantBase.metadata,
        sa.Column("id", sa.SmallInteger, primary_key=True),
        sa.Column("default_transaction_currency", sa.String(3), nullable=False),
        sa.Column("provider_code", sa.String(32), nullable=False),
        sa.Column("rate_date_policy", sa.String(32), nullable=False),
        sa.Column("rounding_mode", sa.String(32), nullable=False),
        sa.Column("allow_cross_rate", sa.Boolean, nullable=False),
        sa.Column("bridge_currency", sa.String(3), nullable=False),
        sa.Column("business_timezone", sa.String(64), nullable=False),
        sa.Column("default_display_currency", sa.String(3)),
        code_check("default_display_currency", "ck_currency_policy_display"),
        sa.Column("version", sa.Integer, nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "id = 1 AND version > 0", name="ck_currency_policy_singleton"
        ),
        sa.CheckConstraint(
            "rate_date_policy IN ('exact','previous_available')",
            name="ck_currency_policy_date",
        ),
        sa.CheckConstraint(
            "rounding_mode IN ('ROUND_HALF_UP','ROUND_HALF_EVEN','ROUND_DOWN','ROUND_UP')",
            name="ck_currency_policy_rounding",
        ),
        code_check("default_transaction_currency", "ck_currency_policy_default"),
        code_check("bridge_currency", "ck_currency_policy_bridge"),
    )


__all__ = ["CurrencyPolicyModel"]
