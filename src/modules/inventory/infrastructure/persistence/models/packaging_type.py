from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class PackagingTypeModel(TenantBase):
    """Хранит форм-фактор тары текущего tenant с точным регистрозависимым кодом."""

    __tablename__ = "packaging_types"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="pk_packaging_types"),
        sa.UniqueConstraint("code", name="uq_packaging_types_code"),
        sa.CheckConstraint(
            "char_length(btrim(code)) > 0", name="ck_packaging_types_code"
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0", name="ck_packaging_types_name"
        ),
    )
    id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    code: Mapped[str] = mapped_column(sa.Text(collation="C"), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
