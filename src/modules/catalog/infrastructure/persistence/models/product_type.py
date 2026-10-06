from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductTypeModel(TenantBase):
    __tablename__ = "catalog_product_types"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_product_types"),
        sa.UniqueConstraint("code", name="uq_catalog_product_types_code"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    code: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    schema_version: Mapped[int] = mapped_column(sa.Integer, nullable=False)


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


class ProductTypeContentBlockModel(TenantBase):
    __tablename__ = "catalog_product_type_content_blocks"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "product_type_id",
            "scope",
            "block_id",
            name="pk_catalog_product_type_content_blocks",
        ),
        sa.ForeignKeyConstraint(
            ["product_type_id"],
            ["tenant.catalog_product_types.id"],
            name="fk_catalog_product_type_blocks_type",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["tenant.catalog_content_block_definitions.id"],
            name="fk_catalog_product_type_blocks_block",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "product_type_id",
            "scope",
            "position",
            name="uq_catalog_product_type_blocks_position",
        ),
        sa.CheckConstraint(
            "scope IN ('product', 'variant')",
            name="ck_catalog_product_type_blocks_scope",
        ),
        sa.CheckConstraint(
            "position >= 0", name="ck_catalog_product_type_blocks_position"
        ),
    )

    product_type_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    scope: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    block_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    required: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
