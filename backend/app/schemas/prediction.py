from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas._datetime_utils import as_utc


class ManualPredictionRequest(BaseModel):
    nitrogen: float = Field(ge=0, le=200)
    phosphorus: float = Field(ge=0, le=200)
    potassium: float = Field(ge=0, le=250)
    temperature: float = Field(ge=-10, le=55)
    humidity: float = Field(ge=0, le=100)
    ph: float = Field(ge=0, le=14)
    rainfall: float = Field(ge=0, le=500)
    moisture: float | None = Field(default=None, ge=0, le=100)
    season: str | None = None
    location: str | None = None


class DeviceBasedPredictionRequest(BaseModel):
    device_uid: str
    season: str | None = None
    location: str | None = None


class CropDetails(BaseModel):
    display_name: str
    image: str
    season: list[str]
    water_requirement: str
    harvest_duration_days: int
    soil_suitability: list[str]
    expected_yield: str


class CropAlternative(BaseModel):
    crop: str
    confidence: float
    suitability_tier: str = "moderate"  # excellent | very_suitable | suitable | moderate
    crop_details: CropDetails | dict = {}


class ExplanationFactor(BaseModel):
    feature: str  # N | P | K | temperature | humidity | ph | rainfall
    level: str  # ideal | low | high


class RecommendationExplanation(BaseModel):
    crop: str
    season: str
    factors: list[ExplanationFactor]


class PredictionResponse(BaseModel):
    id: int | None = None
    recommended_crop: str
    confidence: float
    alternatives: list[CropAlternative]
    feature_importance: dict[str, float]
    crop_details: CropDetails
    season_used: str
    explanation: RecommendationExplanation
    created_at: datetime | None = None

    _tag_created_at_utc = field_validator("created_at", mode="before")(as_utc)


class ModelInfoResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    accuracy: float | None
    cv_mean_accuracy: float | None
    weighted_f1: float | None
    n_classes: int
    classes: list[str]
    model_selected: str | None = None
