from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))

    nitrogen: Mapped[float] = mapped_column(Float, nullable=True)
    phosphorus: Mapped[float] = mapped_column(Float, nullable=True)
    potassium: Mapped[float] = mapped_column(Float, nullable=True)
    moisture: Mapped[float] = mapped_column(Float, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=True)
    humidity: Mapped[float] = mapped_column(Float, nullable=True)
    ph: Mapped[float] = mapped_column(Float, nullable=True)
    rainfall: Mapped[float] = mapped_column(Float, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    device = relationship("Device", back_populates="readings")
