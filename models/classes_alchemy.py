import uuid
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, Double, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    pass

class DMI(Base):
    __tablename__ = "DMI"
    dmi_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, primary_key=True)
    parameter_id: Mapped[str]       = mapped_column(String(50))
    value:        Mapped[float]     = mapped_column(Double())
    observed_at:  Mapped[datetime]  = mapped_column(DateTime(timezone=True))
    pulled_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True))
    station_id:   Mapped[int]       = mapped_column(Integer)

class BME280(Base):
    __tablename__ = "BME280"
    __table_args__ = (CheckConstraint("location IN ('inside', 'outside')", name="check_loc_bme280"),)
    reader_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, primary_key=True)
    location:    Mapped[str]       = mapped_column(String(7), nullable=False)
    humidity:    Mapped[float]     = mapped_column(Numeric(20, 13))
    pressure:    Mapped[float]     = mapped_column(Numeric(20, 13))
    temperature: Mapped[float]     = mapped_column(Numeric(20, 13))
    observed_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True))
    pulled_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True))

class DS18B20(Base):
    __tablename__ = "DS18B20"
    __table_args__ = (CheckConstraint("location IN ('inside', 'outside')", name="check_loc_DS18B20"),)
    reader_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, primary_key=True)
    location:    Mapped[str]       = mapped_column(String(7), nullable=False)
    temperature: Mapped[float]     = mapped_column(Numeric(20, 13))
    observed_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True))
    pulled_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True))

class SCD41(Base):
    __tablename__ = "SCD41"
    reader_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, primary_key=True)
    co2:         Mapped[int]       = mapped_column(Integer)
    humidity:    Mapped[float]     = mapped_column(Numeric(20, 13))
    temperature: Mapped[float]     = mapped_column(Numeric(20, 13))
    observed_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True))
    pulled_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True))