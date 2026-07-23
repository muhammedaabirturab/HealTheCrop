from pydantic import BaseModel, Field


class SoilHealthRequest(BaseModel):
    nitrogen: float | None = Field(default=None, ge=0, le=200)
    phosphorus: float | None = Field(default=None, ge=0, le=200)
    potassium: float | None = Field(default=None, ge=0, le=250)
    ph: float | None = Field(default=None, ge=0, le=14)
    moisture: float | None = Field(default=None, ge=0, le=100)
