from sqlalchemy import (
    CheckConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.audience_mixin import AudienceMixin
from src.modules.shared.infrastructure.persistence.entity_audit_mixin import (
    EntityAuditMixin,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class WarehouseModel(EntityAuditMixin, AudienceMixin, TenantBase):
    """Статическое хранение нового склада в схеме, выбранной Tenancy."""

    __tablename__ = "warehousing_warehouses"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_warehousing_warehouses"),
        UniqueConstraint("code", name="uq_warehousing_warehouses_code"),
        CheckConstraint(
            "char_length(code) BETWEEN 1 AND 64 AND code = upper(btrim(code))",
            name="ck_warehousing_warehouses_code",
        ),
        CheckConstraint(
            "char_length(btrim(title)) BETWEEN 1 AND 255",
            name="ck_warehousing_warehouses_title",
        ),
        CheckConstraint(
            "char_length(btrim(type)) BETWEEN 1 AND 64",
            name="ck_warehousing_warehouses_type",
        ),
        CheckConstraint(
            "char_length(btrim(timezone)) BETWEEN 1 AND 128",
            name="ck_warehousing_warehouses_timezone",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name="ck_warehousing_warehouses_status",
        ),
        CheckConstraint("revision >= 1", name="ck_warehousing_warehouses_revision"),
        CheckConstraint(
            "updated_at >= created_at", name="ck_warehousing_warehouses_audit"
        ),
        Index(
            "ix_warehousing_warehouses_status_type_code", "status", "type", "code", "id"
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    warehouse_type: Mapped[str] = mapped_column("type", String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    timezone: Mapped[str] = mapped_column(String(128), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
