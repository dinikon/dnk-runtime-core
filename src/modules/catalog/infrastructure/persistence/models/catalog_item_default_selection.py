from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemDefaultSelectionModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item_default_selections"
    __table_args__ = (
        sa.CheckConstraint(
            "is_variation", name="ck_catalog_item_default_selections_axis"
        ),
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "attribute_id", "option_id", "is_variation"],
            [
                "tenant.catalog_item_attribute_options.catalog_item_id",
                "tenant.catalog_item_attribute_options.attribute_id",
                "tenant.catalog_item_attribute_options.option_id",
                "tenant.catalog_item_attribute_options.is_variation",
            ],
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    catalog_item_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.catalog_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attribute_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    option_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    is_variation: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.true()
    )
