"""Public reference catalogs and tenant-independent scheduled jobs."""

from alembic import op
import sqlalchemy as sa

revision = "0006_reference_data"
down_revision = "0005_access_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("scheduled_jobs", "tenant_id", nullable=True, schema="public")
    op.create_table(
        "ref_countries",
        sa.Column("code", sa.String(2), primary_key=True),
        sa.Column("alpha3", sa.String(3), nullable=False, unique=True),
        sa.Column("numeric_code", sa.String(3), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        schema="public",
    )
    op.create_table(
        "ref_currencies",
        sa.Column("code", sa.String(3), primary_key=True),
        sa.Column("numeric_code", sa.String(3)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("minor_units", sa.SmallInteger()),
        sa.Column("active", sa.Boolean(), nullable=False),
        schema="public",
    )
    op.create_table(
        "ref_locales",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("language_code", sa.String(8), nullable=False),
        sa.Column("script_code", sa.String(4)),
        sa.Column("region_code", sa.String(3)),
        sa.Column(
            "country_code", sa.String(2), sa.ForeignKey("public.ref_countries.code")
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        schema="public",
    )
    op.create_table(
        "ref_time_zones",
        sa.Column("code", sa.String(128), primary_key=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        schema="public",
    )
    op.create_table(
        "ref_country_time_zones",
        sa.Column(
            "country_code",
            sa.String(2),
            sa.ForeignKey("public.ref_countries.code"),
            primary_key=True,
        ),
        sa.Column(
            "time_zone_code",
            sa.String(128),
            sa.ForeignKey("public.ref_time_zones.code"),
            primary_key=True,
        ),
        schema="public",
    )
    op.create_table(
        "ref_sync_state",
        sa.Column("dataset", sa.String(32), primary_key=True),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("source_version", sa.String(100), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        schema="public",
    )


def downgrade() -> None:
    for table in (
        "ref_sync_state",
        "ref_country_time_zones",
        "ref_time_zones",
        "ref_locales",
        "ref_currencies",
        "ref_countries",
    ):
        op.drop_table(table, schema="public")
    op.alter_column("scheduled_jobs", "tenant_id", nullable=False, schema="public")
