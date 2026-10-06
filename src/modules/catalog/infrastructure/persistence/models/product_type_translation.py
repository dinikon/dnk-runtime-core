from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductTypeTranslationModel(TenantBase):
    __tablename__ = "catalog_product_type_translations"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "product_type_id",
            "locale_code",
            name="pk_catalog_product_type_translations",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"],
            ["tenant.catalog_product_types.id"],
            name="fk_catalog_product_type_translations_type",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_product_type_translation_name",
        ),
    )

    product_type_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    locale_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
