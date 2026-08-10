from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImageQualityInfo(BaseModel):
    is_acceptable: bool
    issues: list[str] = []
    messages: list[str] = []


class SourceCitation(BaseModel):
    title: str
    publisher: str
    url: str | None = None


class PestDetectionItem(BaseModel):
    name: str
    display_name: str
    type: str  # disease | pest | deficiency | healthy
    category: str = "none"  # fungal | bacterial | viral | insect | mite | nematode | deficiency | none
    scientific_name: str | None = None
    applicable_crops: list[str] = []
    confidence: float
    description: str
    severity_level: str = "Moderate"  # Low | Moderate | High | Critical
    organic_treatment: str
    biological_control: str | None = None
    chemical_treatment: str
    recommended_pesticides: list[str]
    recommended_insecticide: str | None = None
    recommended_fungicide: str | None = None
    dosage_guidance: str = "Follow the product label; rates vary by formulation and region."
    safety_precautions: str | None = None
    waiting_period_before_harvest: str | None = None
    prevention_tips: list[str]
    recovery_recommendations: str = ""
    expected_recovery_days: int
    sources: list[SourceCitation] = []
    content_language: str = "en"  # actual language of the text fields above — "en" if the
    # requested language had no translation for this entry (frontend should show a fallback note)
    region: list[int] | None = None  # bounding box [x, y, w, h] on the image


class PestDetectionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int | None = None
    model_used: str
    detections: list[PestDetectionItem]
    severity: str
    image_quality: ImageQualityInfo = ImageQualityInfo(is_acceptable=True)
    is_uncertain: bool = False
    uncertainty_note: str | None = None
    created_at: datetime | None = None
