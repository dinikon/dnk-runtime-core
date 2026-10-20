from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductRepresentationModel(TenantBase):
    """Хранит представление по стабильной паре Connection/Catalog ID."""

    __tablename__ = "channel_product_representations"
    __table_args__ = (
        sa.UniqueConstraint(
            "connection_id", "catalog_item_id", name="uq_channel_representation_pair"
        ),
        sa.CheckConstraint("revision>0", name="ck_channel_representation_revision"),
    )
    id: Mapped[UUID] = mapped_column(sa.UUID(), primary_key=True)
    connection_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_connections.id"), nullable=False
    )
    catalog_item_id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
