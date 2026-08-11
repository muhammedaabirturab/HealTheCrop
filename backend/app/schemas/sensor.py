from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas._datetime_utils import as_utc


class SensorReadingIn(BaseModel):
    device_uid: str = Field(description="Unique ESP32 device identifier")
    nitrogen: float | None = None
    phosphorus: float | None = None
    potassium: float | None = None
    moisture: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    ph: float | None = None
    rainfall: float | None = None


class SensorReadingOut(BaseModel):
    id: int
    device_id: int
    nitrogen: float | None
    phosphorus: float | None
    potassium: float | None
    moisture: float | None
    temperature: float | None
    humidity: float | None
    ph: float | None
    rainfall: float | None
    recorded_at: datetime

    model_config = {"from_attributes": True}

    _tag_recorded_at_utc = field_validator("recorded_at", mode="before")(as_utc)


class DeviceOut(BaseModel):
    id: int
    device_uid: str
    name: str
    location: str | None
    status: str
    last_seen: datetime | None

    model_config = {"from_attributes": True}

    _tag_last_seen_utc = field_validator("last_seen", mode="before")(as_utc)
