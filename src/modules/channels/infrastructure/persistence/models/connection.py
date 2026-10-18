from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ConnectionModel(TenantBase):
    """Описывает tenant-хранение channel_connections без бизнес-переходов."""

    __tablename__ = "channel_connections"
    __table_args__ = (
        sa.UniqueConstraint("channel_id", name="uq_channel_connections_channel"),
        sa.UniqueConstraint("resource_key", name="uq_channel_connections_resource"),
        sa.CheckConstraint("generation >= 0", name="ck_channel_connections_generation"),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False, primary_key=True)
    channel_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("tenant.channels.id"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(sa.String(2048), nullable=False)
    locales: Mapped[list[str]] = mapped_column(JSONB(), nullable=False)
    currency: Mapped[str | None] = mapped_column(sa.String(3), nullable=True)
    credentials_ciphertext: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    candidate_ciphertext: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    resource_identity: Mapped[str | None] = mapped_column(
        sa.String(1000), nullable=True
    )
    resource_key: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    verification_status: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    verification_job_id: Mapped[UUID | None] = mapped_column(sa.UUID(), nullable=True)
    generation: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    is_paused: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    scope_limitations: Mapped[list[str]] = mapped_column(JSONB(), nullable=False)
