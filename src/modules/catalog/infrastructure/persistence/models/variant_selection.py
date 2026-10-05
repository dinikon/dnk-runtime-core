from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class VariantSelectionModel(TenantBase):
    __tablename__ = "catalog_variant_selections"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "variant_id", "attribute_id", name="pk_catalog_variant_selections"
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["tenant.catalog_variants.id"],
            name="fk_catalog_variant_selections_variant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["option_id", "attribute_id"],
            [
                "tenant.catalog_attribute_options.id",
                "tenant.catalog_attribute_options.attribute_id",
            ],
            name="fk_catalog_variant_selections_option_attribute",
        ),
    )

    variant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    attribute_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    option_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
