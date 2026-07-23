from datetime import datetime

from pydantic import BaseModel, Field


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


class DeviceOut(BaseModel):
    id: int
    device_uid: str
    name: str
    location: str | None
    status: str
    last_seen: datetime | None

    model_config = {"from_attributes": True}
