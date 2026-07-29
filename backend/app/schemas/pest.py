from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PestDetectionItem(BaseModel):
    name: str
    display_name: str
    type: str  # disease | pest | deficiency | healthy
    category: str = "none"  # fungal | bacterial | viral | insect | mite | deficiency | none
    confidence: float
    description: str
    severity_level: str = "Moderate"  # Low | Moderate | High | Critical
    organic_treatment: str
    chemical_treatment: str
    recommended_pesticides: list[str]
    recommended_fungicide: str | None = None
    dosage_guidance: str = "Follow the product label; rates vary by formulation and region."
    prevention_tips: list[str]
    recovery_recommendations: str = ""
    expected_recovery_days: int
    region: list[int] | None = None  # bounding box [x, y, w, h] on the image


class PestDetectionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int | None = None
    model_used: str
    detections: list[PestDetectionItem]
    severity: str
    created_at: datetime | None = None
