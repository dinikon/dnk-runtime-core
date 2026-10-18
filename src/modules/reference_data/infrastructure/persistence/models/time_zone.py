from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.shared.infrastructure.persistence.base import Base


class TimeZoneModel(Base):
    __tablename__ = "ref_time_zones"
    __table_args__ = {"schema": "public"}

    code: Mapped[str] = mapped_column(String(128), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CountryTimeZoneModel(Base):
    __tablename__ = "ref_country_time_zones"
    __table_args__ = {"schema": "public"}

    country_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("public.ref_countries.code"), primary_key=True
    )
    time_zone_code: Mapped[str] = mapped_column(
        String(128), ForeignKey("public.ref_time_zones.code"), primary_key=True
    )
