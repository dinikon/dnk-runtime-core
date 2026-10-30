from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.channels.domain.types import JsonObject
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ContentFeedModel(TenantBase):
    """Настройки постоянного фида без хранения XML или истории выдачи."""

    __tablename__ = "channel_content_feeds"
    __table_args__ = (
        sa.UniqueConstraint("connection_id", "scope_key", name="uq_content_feed_scope"),
        sa.CheckConstraint("revision > 0", name="ck_content_feed_revision"),
        sa.CheckConstraint(
            "(access_token_hash IS NULL) = (access_token_encrypted IS NULL)",
            name="ck_content_feed_token",
        ),
        sa.CheckConstraint(
            "NOT enabled OR access_token_hash IS NOT NULL",
            name="ck_content_feed_enabled",
        ),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.channel_connections.id", ondelete="CASCADE")
    )
    scope_key: Mapped[str] = mapped_column(sa.Text)
    revision: Mapped[int] = mapped_column(sa.BigInteger)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.false())
    source_schema: Mapped[str] = mapped_column(sa.Text)
    source_settings: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql")
    )
    source_url_encrypted: Mapped[bytes] = mapped_column(sa.LargeBinary)
    access_token_hash: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
    access_token_encrypted: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(StringUUID)
    updated_by: Mapped[UUID] = mapped_column(StringUUID)
    delivery_schema: Mapped[str] = mapped_column(
        sa.Text, server_default="content_feed_delivery.v1"
    )
    delivery_state: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql"), server_default=sa.text("'{}'")
    )
    delivery_request_encrypted: Mapped[bytes | None] = mapped_column(sa.LargeBinary)
