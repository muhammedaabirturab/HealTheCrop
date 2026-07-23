from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FertilityReport(Base):
    __tablename__ = "fertility_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    sensor_reading_id: Mapped[int] = mapped_column(ForeignKey("sensor_readings.id"), nullable=True)

    fertility_score: Mapped[float] = mapped_column(Float)
    issues: Mapped[list] = mapped_column(JSON)
    suggestions: Mapped[list] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
