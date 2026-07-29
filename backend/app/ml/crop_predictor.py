"""
Loads the trained Random Forest crop-recommendation bundle produced by
ml/scripts/train_model.py and exposes a single predict() call the API uses.
"""
import json
import logging
from pathlib import Path

import joblib
import numpy as np
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
        self.ovr_model = bundle.get("ovr_model")
        if self.ovr_model is not None:
            # Each of the 52 one-vs-rest estimators was trained with n_jobs=-1;
            # left as-is, a single prediction request spins up a fresh joblib
            # worker pool 52 times in a row (very slow, especially on Windows).
            # A single row of inference doesn't benefit from parallelism anyway,
            # so force it off post-training rather than retraining.
            for estimator in self.ovr_model.estimators_:
                estimator.n_jobs = 1
        self.label_encoder = bundle["label_encoder"]
        self.season_encoder = bundle["season_encoder"]
        self.location_encoder = bundle["location_encoder"]
        self.feature_names = bundle["feature_names"]
        self.feature_importances = bundle["feature_importances"]
        self.metrics = bundle.get("metrics", {})
        self.crop_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        logger.info(
            "Loaded crop model with %d classes (held-out accuracy %.4f)",
            len(self.label_encoder.classes_), self.metrics.get("accuracy", 0.0),
        )

    def _safe_encode(self, encoder, value: str) -> int:
        classes = list(encoder.classes_)
        if value in classes:
            return int(encoder.transform([value])[0])
        return int(encoder.transform([classes[0]])[0])  # fall back to a known category

    def _independent_confidences(self, X: pd.DataFrame) -> dict:
        """
        Per-crop suitability score from the one-vs-rest ensemble, each computed
        by its own binary classifier (this crop vs. everything else) with no
        forced normalization across crops — unlike the multiclass model's
        predict_proba, these do NOT sum to 100% across crops, so a strong
        second choice isn't penalized just because the top choice is stronger.
        Bypasses OneVsRestClassifier.predict_proba() itself, which re-normalizes
        rows to sum to 1 and would otherwise undo exactly this property.
        """
        raw = np.array([estimator.predict_proba(X)[0, 1] for estimator in self.ovr_model.estimators_])
        class_names = self.label_encoder.inverse_transform(self.ovr_model.classes_)
        return dict(zip(class_names, raw.tolist()))

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
        classifier_confidence = dict(zip(classes, probabilities.tolist()))

        independent = self._independent_confidences(X)
        ranked_independent = sorted(independent.items(), key=lambda kv: kv[1], reverse=True)

        MIN_CONFIDENCE = 0.50
        MAX_RESULTS = 6
        qualifying = [(crop, score) for crop, score in ranked_independent if score >= MIN_CONFIDENCE][:MAX_RESULTS]
        if not qualifying:
            # Nothing clears the bar independently — still surface the single
            # best guess rather than leaving the farmer with an empty screen.
            qualifying = ranked_independent[:1]

        alternatives = [
            {"crop": crop, "confidence": round(float(score), 4), "crop_details": self.crop_metadata.get(crop, {})}
            for crop, score in qualifying
        ]
        best_crop = qualifying[0][0]
        # "Prediction Confidence" reflects how sure the classifier is that
        # best_crop specifically is the single right answer among all 52
        # crops (a comparative, classification-style measure) — distinct from
        # best_crop's own independent suitability score shown on its card.
        best_conf = classifier_confidence.get(best_crop, 0.0)

        return {
            "recommended_crop": best_crop,
            "confidence": round(float(best_conf), 4),
            "alternatives": alternatives,
            "feature_importance": self.feature_importances,
            "crop_details": self.crop_metadata.get(best_crop, {}),
        }

    def get_crop_details(self, crop_name: str) -> dict:
        return self.crop_metadata.get(crop_name, {})

    def get_model_info(self) -> dict:
        return {
            "accuracy": self.metrics.get("accuracy"),
            "cv_mean_accuracy": self.metrics.get("cv_mean_accuracy"),
            "weighted_f1": self.metrics.get("weighted_f1"),
            "n_classes": len(self.label_encoder.classes_),
            "classes": self.label_encoder.classes_.tolist(),
        }


_predictor: CropPredictor | None = None


def get_crop_predictor() -> CropPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CropPredictor()
    return _predictor
