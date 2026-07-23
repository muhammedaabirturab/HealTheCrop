from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.fertility_report import FertilityReport
from app.models.user import User
from app.services.fertility_service import compute_soil_health, generate_suggestions

router = APIRouter(prefix="/reports", tags=["Soil Health & Fertility"])


@router.post("/soil-health")
def soil_health_report(
    reading: dict = Body(..., examples=[{"nitrogen": 35, "phosphorus": 20, "potassium": 25, "ph": 5.2, "moisture": 28}]),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    health = compute_soil_health(reading)
    suggestions = generate_suggestions(reading) if health["fertility_score"] < 75 else []

    record = FertilityReport(
        user_id=user.id,
        fertility_score=health["fertility_score"],
        issues=[k for k, v in health["indicators"].items() if v["status"] in ("poor", "critical")],
        suggestions=suggestions,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "fertility_score": health["fertility_score"],
        "indicators": health["indicators"],
        "suggestions": suggestions,
        "created_at": record.created_at,
    }


@router.get("/soil-health/history")
def soil_health_history(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    records = (
        db.query(FertilityReport).filter(FertilityReport.user_id == user.id)
        .order_by(FertilityReport.created_at.desc()).limit(limit).all()
    )
    return records
