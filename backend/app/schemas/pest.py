from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PestDetectionItem(BaseModel):
    name: str
    display_name: str
    type: str
    confidence: float
    description: str
    organic_treatment: str
    chemical_treatment: str
    recommended_pesticides: list[str]
    prevention_tips: list[str]
    expected_recovery_days: int
    region: list[int] | None = None  # bounding box [x, y, w, h] on the image


class PestDetectionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int | None = None
    model_used: str
    detections: list[PestDetectionItem]
    severity: str
    created_at: datetime | None = None
