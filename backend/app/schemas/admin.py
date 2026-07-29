from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class AdminStats(BaseModel):
    total_users: int
    total_farmers: int
    total_admins: int
    active_users: int
    deactivated_users: int
    total_predictions: int
    total_pest_scans: int
    total_devices: int
    total_sensor_readings: int


class AdminUserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None
    location: str | None
    preferred_language: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserStatusUpdate(BaseModel):
    is_active: bool


class LoginHistoryOut(BaseModel):
    id: int
    user_id: int | None
    email_attempted: EmailStr
    success: bool
    remember_me: bool
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminPredictionOut(BaseModel):
    id: int
    user_id: int
    user_email: EmailStr | None
    recommended_crop: str
    confidence: float
    season: str | None
    source: str
    created_at: datetime


class AdminPestScanOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int
    user_id: int
    user_email: EmailStr | None
    image_key: str
    model_used: str
    top_confidence: float | None
    detections: list
    created_at: datetime


class AdminSensorReadingOut(BaseModel):
    id: int
    device_id: int
    device_uid: str | None
    nitrogen: float | None
    phosphorus: float | None
    potassium: float | None
    moisture: float | None
    temperature: float | None
    humidity: float | None
    ph: float | None
    rainfall: float | None
    recorded_at: datetime
