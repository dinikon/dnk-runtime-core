from sqlalchemy import Boolean, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.base import Base


class CurrencyModel(Base):
    __tablename__ = "ref_currencies"
    __table_args__ = {"schema": "public"}

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    numeric_code: Mapped[str | None] = mapped_column(String(3))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    minor_units: Mapped[int | None] = mapped_column(SmallInteger)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
