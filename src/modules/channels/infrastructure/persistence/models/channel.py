import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ChannelModel(EntityAuditMixin, AudienceMixin, TenantBase):
    __tablename__ = "channels"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_channels"),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255", name="ck_channel_name"
        ),
        sa.CheckConstraint("config_version >= 1", name="ck_channel_config_version"),
        sa.CheckConstraint(
            "status IN ('unverified', 'connected', 'error')", name="ck_channel_status"
        ),
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    kind: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    config_version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    connection_settings: Mapped[dict] = mapped_column(JSONB, nullable=False)
    encrypted_secrets: Mapped[str] = mapped_column(sa.Text, nullable=False)
    configured_secret_fields: Mapped[list] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
