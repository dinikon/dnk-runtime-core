from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.base import Base


class LocaleModel(Base):
    __tablename__ = "ref_locales"
    __table_args__ = {"schema": "public"}

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    language_code: Mapped[str] = mapped_column(String(8), nullable=False)
    script_code: Mapped[str | None] = mapped_column(String(4))
    region_code: Mapped[str | None] = mapped_column(String(3))
    country_code: Mapped[str | None] = mapped_column(
        String(2), ForeignKey("public.ref_countries.code")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
