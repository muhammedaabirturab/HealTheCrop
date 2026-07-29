import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.core.storage import storage_service
from app.models.device import Device
from app.models.login_history import LoginHistory
from app.models.pest_detection import PestDetection
from app.models.prediction import Prediction
from app.models.sensor_reading import SensorReading
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminPestScanOut, AdminPredictionOut, AdminSensorReadingOut, AdminStats,
    AdminUserOut, LoginHistoryOut, UserStatusUpdate,
)

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/stats", response_model=AdminStats)
def stats(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return AdminStats(
        total_users=len(users),
        total_farmers=sum(1 for u in users if u.role == UserRole.FARMER),
        total_admins=sum(1 for u in users if u.role == UserRole.ADMIN),
        active_users=sum(1 for u in users if u.is_active),
        deactivated_users=sum(1 for u in users if not u.is_active),
        total_predictions=db.query(Prediction).count(),
        total_pest_scans=db.query(PestDetection).count(),
        total_devices=db.query(Device).count(),
        total_sensor_readings=db.query(SensorReading).count(),
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/users/{user_id}", response_model=AdminUserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
def set_user_status(user_id: int, payload: UserStatusUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot deactivate an administrator account")
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Deletes a user along with everything that FK-references them, so the
    delete never leaves orphaned prediction/pest-scan/device rows behind —
    SQLite doesn't enforce foreign keys by default, so this has to be done
    explicitly rather than relying on the database to cascade it."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot delete an administrator account")

    db.query(Prediction).filter(Prediction.user_id == user_id).delete()
    db.query(PestDetection).filter(PestDetection.user_id == user_id).delete()
    device_ids = [d.id for d in db.query(Device.id).filter(Device.owner_id == user_id).all()]
    if device_ids:
        db.query(SensorReading).filter(SensorReading.device_id.in_(device_ids)).delete(synchronize_session=False)
        db.query(Device).filter(Device.owner_id == user_id).delete()
    db.query(LoginHistory).filter(LoginHistory.user_id == user_id).update({"user_id": None})

    db.delete(user)
    db.commit()


@router.get("/login-history", response_model=list[LoginHistoryOut])
def login_history(limit: int = 200, db: Session = Depends(get_db)):
    return (
        db.query(LoginHistory).order_by(LoginHistory.created_at.desc()).limit(limit).all()
    )


@router.get("/predictions", response_model=list[AdminPredictionOut])
def all_predictions(limit: int = 200, db: Session = Depends(get_db)):
    rows = (
        db.query(Prediction, User.email)
        .join(User, Prediction.user_id == User.id)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        AdminPredictionOut(
            id=p.id, user_id=p.user_id, user_email=email, recommended_crop=p.recommended_crop,
            confidence=p.confidence, season=p.season, source=p.source, created_at=p.created_at,
        )
        for p, email in rows
    ]


@router.get("/pest-scans", response_model=list[AdminPestScanOut])
def all_pest_scans(limit: int = 200, db: Session = Depends(get_db)):
    rows = (
        db.query(PestDetection, User.email)
        .join(User, PestDetection.user_id == User.id)
        .order_by(PestDetection.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        AdminPestScanOut(
            id=p.id, user_id=p.user_id, user_email=email, image_key=p.image_key,
            model_used=p.model_used, top_confidence=p.top_confidence,
            detections=p.detections, created_at=p.created_at,
        )
        for p, email in rows
    ]


@router.get("/pest-scans/{scan_id}/image")
def get_pest_scan_image(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(PestDetection).filter(PestDetection.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Pest scan not found")
    image_bytes = storage_service.get_bytes(scan.image_key)
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Image not found in storage")
    return Response(content=image_bytes, media_type="image/jpeg")


@router.get("/sensor-readings", response_model=list[AdminSensorReadingOut])
def all_sensor_readings(limit: int = 200, db: Session = Depends(get_db)):
    rows = (
        db.query(SensorReading, Device.device_uid)
        .join(Device, SensorReading.device_id == Device.id)
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit)
        .all()
    )
    return [
        AdminSensorReadingOut(
            id=r.id, device_id=r.device_id, device_uid=uid,
            nitrogen=r.nitrogen, phosphorus=r.phosphorus, potassium=r.potassium,
            moisture=r.moisture, temperature=r.temperature, humidity=r.humidity,
            ph=r.ph, rainfall=r.rainfall, recorded_at=r.recorded_at,
        )
        for r, uid in rows
    ]


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/users.csv")
def export_users_csv(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    rows = [
        {
            "id": u.id, "name": u.name, "email": u.email, "phone": u.phone or "",
            "location": u.location or "", "role": u.role.value, "is_active": u.is_active,
            "preferred_language": u.preferred_language, "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]
    return _csv_response(rows, "healthecrop_users.csv")


@router.get("/export/predictions.csv")
def export_predictions_csv(db: Session = Depends(get_db)):
    rows_data = (
        db.query(Prediction, User.email)
        .join(User, Prediction.user_id == User.id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    rows = [
        {
            "id": p.id, "user_email": email, "recommended_crop": p.recommended_crop,
            "confidence": p.confidence, "season": p.season or "", "source": p.source,
            "created_at": p.created_at.isoformat(),
        }
        for p, email in rows_data
    ]
    return _csv_response(rows, "healthecrop_predictions.csv")


@router.get("/export/pest-scans.csv")
def export_pest_scans_csv(db: Session = Depends(get_db)):
    rows_data = (
        db.query(PestDetection, User.email)
        .join(User, PestDetection.user_id == User.id)
        .order_by(PestDetection.created_at.desc())
        .all()
    )
    rows = [
        {
            "id": p.id, "user_email": email, "model_used": p.model_used,
            "top_confidence": p.top_confidence if p.top_confidence is not None else "",
            "created_at": p.created_at.isoformat(),
        }
        for p, email in rows_data
    ]
    return _csv_response(rows, "healthecrop_pest_scans.csv")


@router.get("/export/login-history.csv")
def export_login_history_csv(db: Session = Depends(get_db)):
    events = db.query(LoginHistory).order_by(LoginHistory.created_at.desc()).all()
    rows = [
        {
            "id": e.id, "email_attempted": e.email_attempted, "success": e.success,
            "remember_me": e.remember_me, "ip_address": e.ip_address or "",
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
    return _csv_response(rows, "healthecrop_login_history.csv")
