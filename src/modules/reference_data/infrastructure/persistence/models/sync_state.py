from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.base import Base


class ReferenceSyncStateModel(Base):
    __tablename__ = "ref_sync_state"
    __table_args__ = {"schema": "public"}

    dataset: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_version: Mapped[str] = mapped_column(String(100), nullable=False)
    last_success_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
