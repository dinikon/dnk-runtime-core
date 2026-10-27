from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.channels.domain.types import JsonObject
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ConnectionModel(TenantBase):
    """Единственное подключение Channel, его секрет и текущее поколение проверки."""

    __tablename__ = "channel_connections"
    __table_args__ = (
        sa.UniqueConstraint("channel_id", name="uq_channel_connections_channel"),
        sa.UniqueConstraint(
            "identity_namespace", "identity_key", name="uq_channel_connections_identity"
        ),
        sa.CheckConstraint(
            "config_revision > 0 AND config_version > 0",
            name="ck_channel_connections_revision",
        ),
        sa.CheckConstraint(
            "(identity_namespace IS NULL) = (identity_key IS NULL)",
            name="ck_channel_connections_identity",
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        StringUUID, sa.ForeignKey("tenant.channels.id", ondelete="CASCADE")
    )
    config_version: Mapped[int] = mapped_column(sa.Integer)
    endpoint: Mapped[str] = mapped_column(sa.Text)
    settings: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql")
    )
    encrypted_credentials: Mapped[bytes] = mapped_column(sa.LargeBinary)
    config_revision: Mapped[int] = mapped_column(sa.Integer)
    identity_namespace: Mapped[str | None] = mapped_column(sa.String(100))
    identity_key: Mapped[str | None] = mapped_column(sa.String(2048))
    verification: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql")
    )
