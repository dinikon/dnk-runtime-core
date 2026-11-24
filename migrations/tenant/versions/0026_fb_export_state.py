"""Создаёт одно состояние экспорта и публичный адрес на Feed."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0026_fb_export_state"
down_revision = "0025_drop_category_source_locale"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавляет состояние экспорта, диагностики и адрес."""
    op.add_column("fb_feeds", sa.Column("public_link_id", sa.UUID(), nullable=True))
    op.create_unique_constraint(
        "uq_fb_feeds_public_link_id", "fb_feeds", ["public_link_id"]
    )
    op.create_table(
        "fb_export_states",
        sa.Column(
            "feed_id",
            sa.UUID(),
            sa.ForeignKey("fb_feeds.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.Column("job_status", sa.String(16), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("job_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("definition_snapshot", JSONB(), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_validation_policy", sa.String(16), nullable=True),
        sa.Column("last_outcome", sa.String(16), nullable=True),
        sa.Column("last_reason_code", sa.String(64), nullable=True),
        sa.Column("last_is_complete", sa.Boolean(), nullable=True),
        sa.Column("total_items", sa.BigInteger(), nullable=True),
        sa.Column("valid_items", sa.BigInteger(), nullable=True),
        sa.Column("warning_items", sa.BigInteger(), nullable=True),
        sa.Column("rejected_items", sa.BigInteger(), nullable=True),
        sa.Column("active_file_id", sa.UUID(), nullable=True),
        sa.Column("active_format", sa.String(16), nullable=True),
        sa.Column("active_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "job_status IN ('PENDING','RUNNING')", name="ck_fb_export_job"
        ),
        sa.CheckConstraint(
            "last_outcome IN ('PUBLISHED','REJECTED','FAILED')",
            name="ck_fb_export_outcome",
        ),
        sa.CheckConstraint(
            "active_format IN ('csv','xml')", name="ck_fb_export_format"
        ),
    )
    op.create_index("ix_fb_export_active_file", "fb_export_states", ["active_file_id"])
    op.create_table(
        "fb_export_issues",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "feed_id",
            sa.UUID(),
            sa.ForeignKey("fb_export_states.feed_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("publication_id", sa.UUID(), nullable=False),
        sa.Column("field_id", sa.UUID(), nullable=True),
        sa.Column("rule_id", sa.UUID(), nullable=True),
        sa.Column("sku", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("path", JSONB(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('WARNING','ERROR')", name="ck_fb_export_issue_severity"
        ),
    )
    op.create_index("ix_fb_export_issues_feed", "fb_export_issues", ["feed_id", "id"])
    op.create_index(
        "ix_fb_export_issues_severity",
        "fb_export_issues",
        ["feed_id", "severity", "id"],
    )


def downgrade() -> None:
    """Удаляет состояние и публичные адреса фидов."""
    op.drop_table("fb_export_issues")
    op.drop_table("fb_export_states")
    op.drop_constraint("uq_fb_feeds_public_link_id", "fb_feeds", type_="unique")
    op.drop_column("fb_feeds", "public_link_id")
