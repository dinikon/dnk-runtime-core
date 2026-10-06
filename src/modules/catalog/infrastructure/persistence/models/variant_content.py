import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from uuid import UUID


class VariantContentModel(TenantBase):
    __tablename__ = "catalog_variant_contents"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "variant_id", "locale_code", name="pk_catalog_variant_contents"
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["tenant.catalog_variants.id"],
            name="fk_catalog_variant_contents_variant",
            ondelete="CASCADE",
        ),
    )

    variant_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    locale_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
