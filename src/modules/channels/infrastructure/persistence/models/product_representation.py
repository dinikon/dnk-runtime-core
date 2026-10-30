from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.channels.domain.types import JsonObject
from src.modules.shared.infrastructure.persistence.string_uuid import StringUUID
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase


class ProductRepresentationModel(TenantBase):
    """Хранит только overrides и разрешение одной группы; бизнес-правила остаются Domain."""

    __tablename__ = "channel_product_representations"
    __table_args__ = (
        sa.UniqueConstraint("binding_group_id", name="uq_representation_binding_group"),
    )

    id: Mapped[UUID] = mapped_column(StringUUID, primary_key=True)
    binding_group_id: Mapped[UUID] = mapped_column(
        StringUUID,
        sa.ForeignKey("tenant.channel_catalog_binding_groups.id", ondelete="CASCADE"),
    )
    revision: Mapped[int] = mapped_column(sa.Integer)
    export_enabled: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.false())
    overrides_schema: Mapped[str] = mapped_column(sa.Text)
    overrides_data: Mapped[JsonObject] = mapped_column(
        sa.JSON().with_variant(JSONB(), "postgresql")
    )
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(StringUUID)
    updated_by: Mapped[UUID] = mapped_column(StringUUID)
