from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.device import Device
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.schemas.sensor import DeviceOut, SensorReadingIn, SensorReadingOut

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.post("/ingest", response_model=SensorReadingOut, status_code=201)
def ingest_reading(payload: SensorReadingIn, db: Session = Depends(get_db)):
    """
    Called by the ESP32 firmware directly (no user auth — devices authenticate
    via their unique device_uid, matching how field hardware works in practice).
    Auto-registers unseen devices so plug-and-play hardware "just works".
    """
    device = db.query(Device).filter(Device.device_uid == payload.device_uid).first()
    if not device:
        device = Device(device_uid=payload.device_uid, status="online")
        db.add(device)
        db.flush()

    device.status = "online"
    device.last_seen = datetime.now(timezone.utc)

    reading = SensorReading(
        device_id=device.id,
        nitrogen=payload.nitrogen,
        phosphorus=payload.phosphorus,
        potassium=payload.potassium,
        moisture=payload.moisture,
        temperature=payload.temperature,
        humidity=payload.humidity,
        ph=payload.ph,
        rainfall=payload.rainfall,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Device).order_by(Device.last_seen.desc()).all()


@router.get("/devices/{device_uid}/latest", response_model=SensorReadingOut)
def latest_reading(device_uid: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    reading = (
        db.query(SensorReading)
        .filter(SensorReading.device_id == device.id)
        .order_by(SensorReading.recorded_at.desc())
        .first()
    )
    if not reading:
        raise HTTPException(status_code=404, detail="No readings yet for this device")
    return reading


@router.get("/devices/{device_uid}/history", response_model=list[SensorReadingOut])
def reading_history(
    device_uid: str, limit: int = 100, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return (
        db.query(SensorReading)
        .filter(SensorReading.device_id == device.id)
        .order_by(SensorReading.recorded_at.desc())
        .limit(limit)
        .all()
    )
