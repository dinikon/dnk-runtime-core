from uuid import UUID
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogCreationRequestModel(TenantBase):
    """Хранит завершённый идемпотентный результат create+bind, не отдельный агрегат."""

    __tablename__ = "channel_catalog_creation_requests"
    request_key: Mapped[UUID] = mapped_column(sa.UUID(), primary_key=True)
    publication_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_external_publications.id"), nullable=False
    )
    input_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    observed_revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    catalog_item_id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
    representation_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_product_representations.id"), nullable=False
    )
    binding_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_external_bindings.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
