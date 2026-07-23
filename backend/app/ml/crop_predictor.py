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

# Rough agronomic "comfortable" ranges used only to describe *why* a parameter
# looks favorable in plain language — not the model's actual per-crop decision
# boundaries (those are learned and not reducible to simple ranges). Good enough
# for a human-readable explanation without needing per-crop reference data at
# inference time.
_COMFORT_RANGES = {
    "N": (40, 120), "P": (30, 100), "K": (30, 150),
    "ph": (6.0, 7.5), "humidity": (40, 90), "rainfall": (50, 250), "temperature": (15, 35),
}


def _comfort_level(feature_key: str, value: float) -> str | None:
    bounds = _COMFORT_RANGES.get(feature_key)
    if bounds is None:
        return None
    lo, hi = bounds
    if lo <= value <= hi:
        return "ideal"
    if value < lo * 0.6 or value > hi * 1.4:
        return None  # too far off to plausibly be "why this crop was picked"
    return "low" if value < lo else "high"


def build_explanation(features: dict, feature_importance: dict, crop: str, ui_season: str) -> dict:
    """
    Returns structured data — not a hardcoded English sentence — so the frontend
    can compose the "why this crop?" blurb in whichever of the 6 supported
    languages is active, using its own translated phrase templates.
    """
    numeric_map = {
        "N": features["nitrogen"], "P": features["phosphorus"], "K": features["potassium"],
        "temperature": features["temperature"], "humidity": features["humidity"],
        "ph": features["ph"], "rainfall": features["rainfall"],
    }
    ranked = sorted(
        ((k, imp) for k, imp in feature_importance.items() if k in numeric_map),
        key=lambda kv: kv[1], reverse=True,
    )

    factors = []
    for key, _ in ranked:
        level = _comfort_level(key, numeric_map[key])
        if level:
            factors.append({"feature": key, "level": level})
        if len(factors) == 2:
            break

    return {"crop": crop, "season": ui_season, "factors": factors}


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
