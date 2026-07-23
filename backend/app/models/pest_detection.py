from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PestDetection(Base):
    __tablename__ = "pest_detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    image_key: Mapped[str] = mapped_column(String(255))
    detections: Mapped[list] = mapped_column(JSON)
    model_used: Mapped[str] = mapped_column(String(20), default="heuristic")  # heuristic | cnn
    top_confidence: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="pest_detections")
