import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from src.modules.shared.infrastructure.persistence import Base, TenantBase, StringUUID


def timestamps():
    return [
        sa.Column(
            name,
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        for name in ("created_at", "updated_at")
    ]


def code_check(column, name):
    return sa.CheckConstraint(f"{column} ~ '^[A-Z]{{3}}$'", name=name).ddl_if(
        dialect="postgresql"
    )


class CurrencyModel(Base):
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


def rate_table(name, metadata, *, provider):
    keys = (["provider_code"] if provider else []) + [
        "source_currency",
        "target_currency",
        "effective_date",
    ]
    columns = [
        sa.Column("id", StringUUID, primary_key=True),
        sa.Column("source_currency", sa.String(3), nullable=False),
        sa.Column("target_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("is_current", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]
    if provider:
        columns += [
            sa.Column("provider_code", sa.String(32), nullable=False),
            sa.Column("calculated_date", sa.Date),
            sa.Column("published_at", sa.DateTime(timezone=True)),
            sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payload_hash", sa.String(64), nullable=False),
        ]
    else:
        columns += [sa.Column("created_by", StringUUID, nullable=False)]
    table = sa.Table(
        name,
        metadata,
        *columns,
        sa.UniqueConstraint(*keys, "revision", name=f"uq_{name}_revision"),
        sa.CheckConstraint(
            "rate > 0 AND rate < 'Infinity'", name=f"ck_{name}_positive"
        ),
        sa.CheckConstraint("revision > 0", name=f"ck_{name}_revision"),
        sa.CheckConstraint(
            "source_currency <> target_currency", name=f"ck_{name}_pair"
        ),
        code_check("source_currency", f"ck_{name}_source"),
        code_check("target_currency", f"ck_{name}_target"),
    )
    sa.Index(
        f"uq_{name}_current",
        *(table.c[k] for k in keys),
        unique=True,
        postgresql_where=table.c.is_current,
        sqlite_where=table.c.is_current,
    )
    sa.Index(
        f"ix_{name}_lookup",
        *(table.c[k] for k in keys[:-1]),
        table.c.effective_date.desc(),
        postgresql_where=table.c.is_current,
        sqlite_where=table.c.is_current,
    )
    return table


class ProviderRateModel(Base):
    __table__ = rate_table("fx_provider_rate", Base.metadata, provider=True)


class RateImportModel(Base):
    __table__ = sa.Table(
        "fx_rate_import",
        Base.metadata,
        sa.Column("id", StringUUID, primary_key=True),
        sa.Column("provider_code", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("requested_date_from", sa.Date, nullable=False),
        sa.Column("requested_date_to", sa.Date, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        *(
            sa.Column(n, sa.Integer, nullable=False, server_default="0")
            for n in ("received_count", "created_count", "updated_count", "error_count")
        ),
        sa.Column("error_message", sa.String(1000)),
        sa.CheckConstraint(
            "status IN ('running','succeeded','failed')", name="ck_fx_import_status"
        ),
        sa.Index("ix_fx_import_provider_started", "provider_code", "started_at"),
    )


class CurrencyPolicyModel(TenantBase):
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


class EnabledCurrencyModel(TenantBase):
    __table__ = sa.Table(
        "enabled_currency",
        TenantBase.metadata,
        sa.Column("currency_code", sa.String(3), primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False),
        *timestamps(),
        code_check("currency_code", "ck_enabled_currency_code"),
    )


class FunctionalCurrencyPeriodModel(TenantBase):
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


class ManualExchangeRateModel(TenantBase):
    __table__ = rate_table("manual_exchange_rate", TenantBase.metadata, provider=False)
