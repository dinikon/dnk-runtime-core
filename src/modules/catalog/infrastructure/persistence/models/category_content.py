from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class CategoryContentModel(TenantBase):
    __tablename__ = "catalog_category_contents"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "category_id", "locale_code", name="pk_catalog_category_contents"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["tenant.catalog_categories.id"],
            name="fk_catalog_category_contents_category",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_category_contents_name",
        ),
    )

    category_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    locale_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
