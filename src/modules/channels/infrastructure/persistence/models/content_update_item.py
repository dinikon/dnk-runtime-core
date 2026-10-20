from uuid import UUID
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


class ContentUpdateItemModel(TenantBase):
    """Хранит внутреннюю позицию операции без независимого repository."""

    __tablename__ = "channel_content_update_items"
    __table_args__ = (
        sa.CheckConstraint(
            "binding_revision > 0 AND attempts >= 0",
            name="ck_content_update_item_revision",
        ),
        sa.CheckConstraint(
            "status IN ('preview_pending','ready','blocked','unchanged','pending','sending','verifying','succeeded','failed','unknown','stale','reconciling')",
            name="ck_content_update_item_status",
        ),
        sa.Index("ix_content_update_item_publication", "publication_id", "run_id"),
    )
    run_id: Mapped[UUID] = mapped_column(
        sa.UUID(),
        sa.ForeignKey("channel_content_update_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    publication_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_external_publications.id"), primary_key=True
    )
    catalog_item_id: Mapped[UUID] = mapped_column(sa.UUID(), nullable=False)
    binding_id: Mapped[UUID] = mapped_column(
        sa.UUID(), sa.ForeignKey("channel_external_bindings.id"), nullable=False
    )
    binding_revision: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    resource_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    external_id: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    provider_context: Mapped[dict[str, JsonValue]] = mapped_column(
        JSONB(), nullable=False
    )
    desired: Mapped[dict[str, JsonValue]] = mapped_column(JSONB(), nullable=False)
    observed: Mapped[dict[str, JsonValue] | None] = mapped_column(
        JSONB(), nullable=True
    )
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    issues: Mapped[list[str]] = mapped_column(JSONB(), nullable=False)
    attempts: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
