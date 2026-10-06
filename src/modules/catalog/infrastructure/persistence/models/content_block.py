from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ContentBlockDefinitionModel(TenantBase):
    __tablename__ = "catalog_content_block_definitions"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_catalog_content_block_definitions"),
        sa.UniqueConstraint("code", name="uq_catalog_content_block_definitions_code"),
        sa.CheckConstraint(
            "type IN ('text', 'rich_text')", name="ck_catalog_content_block_type"
        ),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    code: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)


class ContentBlockTranslationModel(TenantBase):
    __tablename__ = "catalog_content_block_translations"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "block_id", "locale_code", name="pk_catalog_content_block_translations"
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["tenant.catalog_content_block_definitions.id"],
            name="fk_catalog_content_block_translations_block",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) BETWEEN 1 AND 255",
            name="ck_catalog_content_block_translation_name",
        ),
    )

    block_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    locale_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
