"""Добавляет независимо отзываемые токены фидов."""

from alembic import op
import sqlalchemy as sa

revision = "0027_fb_private_access"
down_revision = "0026_fb_export_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создаёт таблицу ключей, сохраняя существующие настройки нетронутыми."""
    op.create_table(
        "fb_access_keys",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "feed_id",
            sa.UUID(),
            sa.ForeignKey("fb_feeds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "feed_id", "token_hash", name="uq_fb_access_keys_feed_digest"
        ),
        sa.CheckConstraint(
            "octet_length(token_hash) = 32", name="ck_fb_access_keys_digest"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_fb_access_keys_name"
        ),
        sa.CheckConstraint("expires_at > created_at", name="ck_fb_access_keys_expiry"),
        sa.CheckConstraint(
            "revoked_at >= created_at", name="ck_fb_access_keys_revoked"
        ),
    )
    op.create_index(
        "ix_fb_access_keys_feed_created",
        "fb_access_keys",
        ["feed_id", "created_at", "id"],
    )


def downgrade() -> None:
    """Сохраняет приватность при откате схемы."""
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE fb_feeds IN ACCESS EXCLUSIVE MODE"))
    if connection.scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM fb_feeds "
            "WHERE export_settings ? 'access_mode' "
            "AND (export_settings ->> 'access_mode') IS DISTINCT FROM 'PUBLIC')"
        )
    ):
        raise RuntimeError("Откат открыл бы доступ к приватным фидам.")
    connection.execute(
        sa.text(
            "UPDATE fb_feeds SET export_settings = export_settings - 'access_mode' "
            "WHERE export_settings ? 'access_mode'"
        )
    )
    op.drop_table("fb_access_keys")
