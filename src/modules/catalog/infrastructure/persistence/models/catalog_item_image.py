from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemImageModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item_images"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "locale"],
            [
                "tenant.catalog_item_galleries.catalog_item_id",
                "tenant.catalog_item_galleries.locale",
            ],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "catalog_item_id", "locale", "id", name="uq_catalog_image_owner"
        ),
        sa.UniqueConstraint(
            "catalog_item_id", "locale", "file_id", name="uq_catalog_image_file"
        ),
        sa.UniqueConstraint(
            "catalog_item_id", "locale", "position", name="uq_catalog_image_position"
        ),
        sa.CheckConstraint("position>=0", name="ck_catalog_image_position"),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    catalog_item_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    locale: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    file_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False, index=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    alt: Mapped[str] = mapped_column(sa.String(1000), nullable=False)
    caption: Mapped[str] = mapped_column(sa.String(5000), nullable=False)
