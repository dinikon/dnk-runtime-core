from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class StockExecutionLedgerLinkModel(TenantBase):
    """Хранит собственные данные учётного факта без бизнес-поведения."""

    __tablename__ = "stock_execution_ledger_links"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "execution_line_id", "role", name="pk_stock_execution_ledger_links"
        ),
        sa.ForeignKeyConstraint(
            ["execution_line_id"],
            ["tenant.stock_execution_lines.id"],
            name="fk_execution_link_line",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ledger_entry_id"],
            ["tenant.stock_ledger_entries.id"],
            name="fk_execution_link_entry",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "role IN ('SOURCE','DESTINATION')", name="ck_execution_link_role"
        ),
    )
    execution_line_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
    role: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    ledger_entry_id: Mapped[UUID] = mapped_column(StringUUID, nullable=False)
