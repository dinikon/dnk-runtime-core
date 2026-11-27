from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class FeedAccessKeyModel(TenantBase):
    """Хранит метаданные и digest выпущенного токена в схеме tenant."""

    __tablename__ = "fb_access_keys"
    __table_args__ = (
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
        sa.Index("ix_fb_access_keys_feed_created", "feed_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    feed_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.fb_feeds.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    token_hash: Mapped[bytes] = mapped_column(sa.LargeBinary(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
