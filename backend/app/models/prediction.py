from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    input_features: Mapped[dict] = mapped_column(JSON)
    recommended_crop: Mapped[str] = mapped_column(String(60))
    confidence: Mapped[float] = mapped_column(Float)
    alternatives: Mapped[list] = mapped_column(JSON)
    season: Mapped[str] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | sensor

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="predictions")
