from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.ml.crop_predictor import build_explanation, get_crop_predictor
from app.models.device import Device
from app.models.prediction import Prediction
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.schemas.prediction import DeviceBasedPredictionRequest, ManualPredictionRequest, PredictionResponse
from app.utils.season import resolve_season

router = APIRouter(prefix="/predictions", tags=["Crop Recommendation"])


def _to_response(record: Prediction, result: dict, ui_season: str, features: dict) -> PredictionResponse:
    return PredictionResponse(
        id=record.id,
        recommended_crop=result["recommended_crop"],
        confidence=result["confidence"],
        alternatives=result["alternatives"],
        feature_importance=result["feature_importance"],
        crop_details=result["crop_details"] or {
            "display_name": result["recommended_crop"].title(),
            "image": "placeholder.jpg", "season": [ui_season], "water_requirement": "Medium",
            "harvest_duration_days": 100, "soil_suitability": ["Loamy"], "expected_yield": "N/A",
        },
        season_used=ui_season,
        explanation=build_explanation(features, result["feature_importance"], result["recommended_crop"], ui_season),
        created_at=record.created_at,
    )


@router.post("/manual", response_model=PredictionResponse)
def predict_manual(
    payload: ManualPredictionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    features = {
        "nitrogen": payload.nitrogen, "phosphorus": payload.phosphorus, "potassium": payload.potassium,
        "temperature": payload.temperature, "humidity": payload.humidity, "ph": payload.ph, "rainfall": payload.rainfall,
    }
    model_season, ui_season = resolve_season(payload.season)
    predictor = get_crop_predictor()
    result = predictor.predict(features, model_season, payload.location or user.location or "Karnataka")

    record = Prediction(
        user_id=user.id, input_features=features, recommended_crop=result["recommended_crop"],
        confidence=result["confidence"], alternatives=result["alternatives"], season=ui_season, source="manual",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_response(record, result, ui_season, features)


@router.post("/from-device", response_model=PredictionResponse)
def predict_from_device(
    payload: DeviceBasedPredictionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.device_uid == payload.device_uid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    reading = (
        db.query(SensorReading).filter(SensorReading.device_id == device.id)
        .order_by(SensorReading.recorded_at.desc()).first()
    )
    if not reading:
        raise HTTPException(status_code=404, detail="No sensor readings available for this device yet")

    features = {
        "nitrogen": reading.nitrogen or 0, "phosphorus": reading.phosphorus or 0, "potassium": reading.potassium or 0,
        "temperature": reading.temperature or 25, "humidity": reading.humidity or 60,
        "ph": reading.ph or 6.5, "rainfall": reading.rainfall or 100,
    }
    model_season, ui_season = resolve_season(payload.season)
    predictor = get_crop_predictor()
    result = predictor.predict(features, model_season, payload.location or user.location or "Karnataka")

    record = Prediction(
        user_id=user.id, input_features=features, recommended_crop=result["recommended_crop"],
        confidence=result["confidence"], alternatives=result["alternatives"], season=ui_season, source="sensor",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_response(record, result, ui_season, features)


@router.get("/history", response_model=list[PredictionResponse])
def prediction_history(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    predictor = get_crop_predictor()
    records = (
        db.query(Prediction).filter(Prediction.user_id == user.id)
        .order_by(Prediction.created_at.desc()).limit(limit).all()
    )
    responses = []
    for record in records:
        details = predictor.get_crop_details(record.recommended_crop) or {
            "display_name": record.recommended_crop.title(), "image": "placeholder.jpg",
            "season": [record.season], "water_requirement": "Medium", "harvest_duration_days": 100,
            "soil_suitability": ["Loamy"], "expected_yield": "N/A",
        }
        responses.append(PredictionResponse(
            id=record.id, recommended_crop=record.recommended_crop, confidence=record.confidence,
            alternatives=record.alternatives, feature_importance=predictor.feature_importances,
            crop_details=details, season_used=record.season,
            explanation=build_explanation(
                record.input_features, predictor.feature_importances, record.recommended_crop, record.season
            ),
            created_at=record.created_at,
        ))
    return responses
