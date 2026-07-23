"""
Loads the trained Random Forest crop-recommendation bundle produced by
ml/scripts/train_model.py and exposes a single predict() call the API uses.
"""
import json
import logging
from pathlib import Path

import joblib
import pandas as pd

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_BASE_DIR = Path(__file__).resolve().parents[2]  # backend/app/ml -> backend/


class CropPredictor:
    def __init__(self):
        model_path = (_BASE_DIR / settings.CROP_MODEL_PATH).resolve()
        metadata_path = (_BASE_DIR / settings.CROP_METADATA_PATH).resolve()

        if not model_path.exists():
            raise FileNotFoundError(
                f"Crop model not found at {model_path}. Run "
                "`python ml/scripts/generate_dataset.py && python ml/scripts/train_model.py` first."
            )

        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.label_encoder = bundle["label_encoder"]
        self.season_encoder = bundle["season_encoder"]
        self.location_encoder = bundle["location_encoder"]
        self.feature_names = bundle["feature_names"]
        self.feature_importances = bundle["feature_importances"]
        self.crop_metadata = json.loads(metadata_path.read_text())
        logger.info("Loaded crop model with %d classes", len(self.label_encoder.classes_))

    def _safe_encode(self, encoder, value: str) -> int:
        classes = list(encoder.classes_)
        if value in classes:
            return int(encoder.transform([value])[0])
        return int(encoder.transform([classes[0]])[0])  # fall back to a known category

    def predict(self, features: dict, season: str, location: str = "Karnataka") -> dict:
        row = {
            "N": features["nitrogen"],
            "P": features["phosphorus"],
            "K": features["potassium"],
            "temperature": features["temperature"],
            "humidity": features["humidity"],
            "ph": features["ph"],
            "rainfall": features["rainfall"],
            "season": self._safe_encode(self.season_encoder, season),
            "location": self._safe_encode(self.location_encoder, location or "Karnataka"),
        }
        X = pd.DataFrame([row])[self.feature_names]

        probabilities = self.model.predict_proba(X)[0]
        classes = self.label_encoder.classes_
        ranked = sorted(zip(classes, probabilities), key=lambda x: x[1], reverse=True)

        top5 = [
            {"crop": crop, "confidence": round(float(p), 4), "crop_details": self.crop_metadata.get(crop, {})}
            for crop, p in ranked[:5]
        ]
        best_crop, best_conf = ranked[0]

        return {
            "recommended_crop": best_crop,
            "confidence": round(float(best_conf), 4),
            "alternatives": top5,
            "feature_importance": self.feature_importances,
            "crop_details": self.crop_metadata.get(best_crop, {}),
        }

    def get_crop_details(self, crop_name: str) -> dict:
        return self.crop_metadata.get(crop_name, {})


_predictor: CropPredictor | None = None


def get_crop_predictor() -> CropPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CropPredictor()
    return _predictor
