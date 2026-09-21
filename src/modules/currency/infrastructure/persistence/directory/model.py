from __future__ import annotations
import sqlalchemy as sa
from src.modules.currency.infrastructure.persistence.schema import code_check
from src.modules.currency.infrastructure.persistence.schema import timestamps
from src.modules.shared.infrastructure.persistence import Base


class CurrencyModel(Base):
    """Persistence mapping for currency."""

    __table__ = sa.Table(
        "currency",
        Base.metadata,
        sa.Column("code", sa.String(3), primary_key=True),
        sa.Column("numeric_code", sa.String(3)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("minor_units", sa.SmallInteger),
        sa.Column("symbol", sa.String(16)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("valid_from", sa.Date),
        sa.Column("valid_to", sa.Date),
        *timestamps(),
        code_check("code", "ck_currency_code"),
        sa.CheckConstraint(
            "minor_units IS NULL OR minor_units BETWEEN 0 AND 9",
            name="ck_currency_minor_units",
        ),
    )


__all__ = ["CurrencyModel"]
