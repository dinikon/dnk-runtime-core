"""Currency directory and rates."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_currency"
down_revision = "0005_access_roles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "currency",
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("numeric_code", sa.String(length=3), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("minor_units", sa.SmallInteger(), nullable=True),
        sa.Column("symbol", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
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
        sa.CheckConstraint("code ~ '^[A-Z]{3}$'", name="ck_currency_code"),
        sa.CheckConstraint(
            "minor_units IS NULL OR minor_units BETWEEN 0 AND 9",
            name="ck_currency_minor_units",
        ),
        sa.PrimaryKeyConstraint("code"),
        schema="public",
    )
    op.create_table(
        "fx_provider_rate",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_currency", sa.String(length=3), nullable=False),
        sa.Column("target_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_code", sa.String(length=32), nullable=False),
        sa.Column("calculated_date", sa.Date(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "rate > 0 AND rate < 'Infinity'", name="ck_fx_provider_rate_positive"
        ),
        sa.CheckConstraint(
            "source_currency ~ '^[A-Z]{3}$'", name="ck_fx_provider_rate_source"
        ),
        sa.CheckConstraint(
            "target_currency ~ '^[A-Z]{3}$'", name="ck_fx_provider_rate_target"
        ),
        sa.CheckConstraint("revision > 0", name="ck_fx_provider_rate_revision"),
        sa.CheckConstraint(
            "source_currency <> target_currency", name="ck_fx_provider_rate_pair"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_code",
            "source_currency",
            "target_currency",
            "effective_date",
            "revision",
            name="uq_fx_provider_rate_revision",
        ),
        schema="public",
    )
    op.create_index(
        "ix_fx_provider_rate_lookup",
        "fx_provider_rate",
        [
            "provider_code",
            "source_currency",
            "target_currency",
            sa.literal_column("effective_date DESC"),
        ],
        unique=False,
        schema="public",
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "uq_fx_provider_rate_current",
        "fx_provider_rate",
        ["provider_code", "source_currency", "target_currency", "effective_date"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("is_current"),
    )
    op.create_table(
        "fx_rate_import",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider_code", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_date_from", sa.Date(), nullable=False),
        sa.Column("requested_date_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("received_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "status IN ('running','succeeded','failed')", name="ck_fx_import_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_fx_import_provider_started",
        "fx_rate_import",
        ["provider_code", "started_at"],
        unique=False,
        schema="public",
    )

    import json
    from pathlib import Path

    seed = json.loads(
        (Path(__file__).parents[1] / "data" / "iso4217.json").read_text()
    )["currencies"]
    table = sa.table(
        "currency",
        sa.column("code"),
        sa.column("numeric_code"),
        sa.column("name"),
        sa.column("minor_units"),
        sa.column("is_active"),
        schema="public",
    )
    op.get_bind().execute(
        postgresql.insert(table)
        .values(seed)
        .on_conflict_do_nothing(index_elements=["code"])
    )


def downgrade():
    op.drop_table("fx_rate_import", schema="public")
    op.drop_table("fx_provider_rate", schema="public")
    op.drop_table("currency", schema="public")
