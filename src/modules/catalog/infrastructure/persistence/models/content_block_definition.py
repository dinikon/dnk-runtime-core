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
