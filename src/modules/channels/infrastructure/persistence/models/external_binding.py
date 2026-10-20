from uuid import UUID
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ExternalBindingModel(TenantBase):
    """Хранит активную основную связь и неизменяемые факты её снятия."""

    __tablename__ = "channel_external_bindings"
    __table_args__ = (
        sa.Index(
            "uq_channel_binding_publication_active",
            "publication_id",
            unique=True,
            postgresql_where=sa.text("released_at IS NULL"),
        ),
        sa.Index(
            "uq_channel_binding_representation_active",
            "representation_id",
            unique=True,
            postgresql_where=sa.text("released_at IS NULL"),
        ),
        sa.CheckConstraint(
            "(released_at IS NULL)=(released_by IS NULL)",
            name="ck_channel_binding_release",
        ),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), primary_key=True)
    representation_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_product_representations.id"), nullable=False
    )
    publication_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_external_publications.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    released_by: Mapped[UUID | None] = mapped_column(sa.UUID(), nullable=True)
