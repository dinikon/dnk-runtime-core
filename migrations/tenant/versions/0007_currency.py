"""Currency directory and rates."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_currency"
down_revision = "0006_price_list_streaming"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "currency_policy",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("default_transaction_currency", sa.String(length=3), nullable=False),
        sa.Column("provider_code", sa.String(length=32), nullable=False),
        sa.Column("rate_date_policy", sa.String(length=32), nullable=False),
        sa.Column("rounding_mode", sa.String(length=32), nullable=False),
        sa.Column("allow_cross_rate", sa.Boolean(), nullable=False),
        sa.Column("bridge_currency", sa.String(length=3), nullable=False),
        sa.Column("business_timezone", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "bridge_currency ~ '^[A-Z]{3}$'", name="ck_currency_policy_bridge"
        ),
        sa.CheckConstraint(
            "default_transaction_currency ~ '^[A-Z]{3}$'",
            name="ck_currency_policy_default",
        ),
        sa.CheckConstraint(
            "rate_date_policy IN ('exact','previous_available')",
            name="ck_currency_policy_date",
        ),
        sa.CheckConstraint(
            "rounding_mode IN ('ROUND_HALF_UP','ROUND_HALF_EVEN','ROUND_DOWN','ROUND_UP')",
            name="ck_currency_policy_rounding",
        ),
        sa.CheckConstraint(
            "id = 1 AND version > 0", name="ck_currency_policy_singleton"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "enabled_currency",
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'", name="ck_enabled_currency_code"
        ),
        sa.PrimaryKeyConstraint("currency_code"),
    )
    op.create_table(
        "functional_currency_period",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        postgresql.ExcludeConstraint(
            (sa.text("daterange(valid_from, valid_to, '[]')"), "&&"),
            using="gist",
            name="ex_functional_currency_period",
        ),
        sa.CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'", name="ck_functional_currency_code"
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_functional_currency_dates",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_functional_currency_from",
        "functional_currency_period",
        ["valid_from"],
        unique=False,
    )
    op.create_table(
        "manual_exchange_rate",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_currency", sa.String(length=3), nullable=False),
        sa.Column("target_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "rate > 0 AND rate < 'Infinity'", name="ck_manual_exchange_rate_positive"
        ),
        sa.CheckConstraint(
            "source_currency ~ '^[A-Z]{3}$'", name="ck_manual_exchange_rate_source"
        ),
        sa.CheckConstraint(
            "target_currency ~ '^[A-Z]{3}$'", name="ck_manual_exchange_rate_target"
        ),
        sa.CheckConstraint("revision > 0", name="ck_manual_exchange_rate_revision"),
        sa.CheckConstraint(
            "source_currency <> target_currency", name="ck_manual_exchange_rate_pair"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_currency",
            "target_currency",
            "effective_date",
            "revision",
            name="uq_manual_exchange_rate_revision",
        ),
    )
    op.create_index(
        "ix_manual_exchange_rate_lookup",
        "manual_exchange_rate",
        [
            "source_currency",
            "target_currency",
            sa.literal_column("effective_date DESC"),
        ],
        unique=False,
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "uq_manual_exchange_rate_current",
        "manual_exchange_rate",
        ["source_currency", "target_currency", "effective_date"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )


def downgrade():
    op.drop_table("manual_exchange_rate")
    op.drop_table("functional_currency_period")
    op.drop_table("enabled_currency")
    op.drop_table("currency_policy")
