from __future__ import annotations
from sqlalchemy.dialects.postgresql import ExcludeConstraint
import sqlalchemy as sa
from src.modules.currency.infrastructure.persistence.schema import code_check
from src.modules.shared.infrastructure.persistence import StringUUID
from src.modules.shared.infrastructure.persistence import TenantBase


class FunctionalCurrencyPeriodModel(TenantBase):
    """Persistence mapping for functional currency period."""

    __table__ = sa.Table(
        "functional_currency_period",
        TenantBase.metadata,
        sa.Column("id", StringUUID, primary_key=True),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("valid_to", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", StringUUID, nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("activation_emitted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_functional_currency_dates",
        ),
        code_check("currency_code", "ck_functional_currency_code"),
        ExcludeConstraint(
            (
                sa.func.daterange(sa.column("valid_from"), sa.column("valid_to"), "[]"),
                "&&",
            ),
            name="ex_functional_currency_period",
            using="gist",
        ).ddl_if(dialect="postgresql"),
        sa.Index("ix_functional_currency_from", "valid_from"),
    )


__all__ = ["FunctionalCurrencyPeriodModel"]
