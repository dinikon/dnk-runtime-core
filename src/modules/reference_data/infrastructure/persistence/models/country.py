from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.base import Base


class CountryModel(Base):
    __tablename__ = "ref_countries"
    __table_args__ = {"schema": "public"}

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    alpha3: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    numeric_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
