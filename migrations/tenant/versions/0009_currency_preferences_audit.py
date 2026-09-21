"""Display preferences, activation delivery and deduplicated failure audit."""

from alembic import op
import sqlalchemy as sa

revision = "0009_currency_preferences_audit"
down_revision = "0008_offer_money"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "currency_policy", sa.Column("default_display_currency", sa.String(3))
    )
    op.create_check_constraint(
        "ck_currency_policy_display",
        "currency_policy",
        "default_display_currency IS NULL OR default_display_currency ~ '^[A-Z]{3}$'",
    )
    op.add_column("users", sa.Column("display_currency", sa.String(3)))
    op.create_check_constraint(
        "ck_users_display_currency",
        "users",
        "display_currency IS NULL OR display_currency ~ '^[A-Z]{3}$'",
    )
    op.add_column(
        "functional_currency_period",
        sa.Column("activation_emitted_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "currency_resolution_failure",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("operation_id", sa.UUID(), nullable=False),
        sa.Column("source_currency", sa.String(3), nullable=False),
        sa.Column("target_currency", sa.String(3)),
        sa.Column("business_date", sa.Date(), nullable=True),
        sa.Column("provider_code", sa.String(32)),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deduplication_key", sa.String(64), nullable=False, unique=True),
        sa.CheckConstraint(
            "source_currency ~ '^[A-Z]{3}$'", name="ck_currency_failure_source"
        ),
        sa.CheckConstraint(
            "target_currency IS NULL OR target_currency ~ '^[A-Z]{3}$'",
            name="ck_currency_failure_target",
        ),
        sa.CheckConstraint(
            "policy_version >= 0", name="ck_currency_failure_policy_version"
        ),
    )
    op.create_index(
        "ix_currency_resolution_failure_operation",
        "currency_resolution_failure",
        ["operation_id"],
    )


def downgrade():
    op.drop_table("currency_resolution_failure")
    op.drop_column("functional_currency_period", "activation_emitted_at")
    op.drop_constraint("ck_users_display_currency", "users", type_="check")
    op.drop_column("users", "display_currency")
    op.drop_constraint("ck_currency_policy_display", "currency_policy", type_="check")
    op.drop_column("currency_policy", "default_display_currency")
