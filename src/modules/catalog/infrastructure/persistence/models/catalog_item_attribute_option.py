from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CatalogItemAttributeOptionModel(TenantBase):
    """Нормализованное tenant-хранение; инварианты находятся в Domain."""

    __tablename__ = "catalog_item_attribute_options"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["catalog_item_id", "attribute_id", "is_variation"],
            [
                "tenant.catalog_item_attributes.catalog_item_id",
                "tenant.catalog_item_attributes.attribute_id",
                "tenant.catalog_item_attributes.is_variation",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["attribute_id", "option_id"],
            [
                "tenant.catalog_attribute_options.attribute_id",
                "tenant.catalog_attribute_options.id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "catalog_item_id",
            "attribute_id",
            "option_id",
            "is_variation",
            name="uq_catalog_item_allowed_option",
        ),
        sa.UniqueConstraint(
            "catalog_item_id",
            "attribute_id",
            "position",
            name="uq_catalog_item_option_position",
        ),
        sa.CheckConstraint("position>=0", name="ck_catalog_item_option_position"),
    )
    catalog_item_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    attribute_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    option_id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    is_variation: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
