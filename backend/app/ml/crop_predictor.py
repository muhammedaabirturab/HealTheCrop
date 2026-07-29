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
    "moisture": (35, 80),
}


SUITABILITY_NUMERIC_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "moisture"]

# Suitability score tiers — thresholds are inclusive lower bounds, checked
# highest-first.
SUITABILITY_TIERS = [
    (0.95, "excellent"),
    (0.85, "very_suitable"),
    (0.70, "suitable"),
    (0.50, "moderate"),
    (0.0, "poor"),
]


def _suitability_tier(score: float) -> str:
    for threshold, tier in SUITABILITY_TIERS:
        if score >= threshold:
            return tier
    return "poor"


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
        "moisture": features.get("moisture", 50.0),
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
        self.crop_feature_stats = bundle.get("crop_feature_stats", {})
        self.crop_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        # Crops grown year-round (season == "Annual" in their metadata) can
        # never be scored fairly against the farmer's UI-selected season: the
        # farmer-facing season picker only ever resolves to Kharif/Rabi/Zaid
        # (see app/utils/season.py), so an Annual crop's season feature would
        # always mismatch training data where it's 100% labeled "Annual" —
        # systematically depressing its model confidence regardless of how
        # well its other features match. Handled in predict() below by also
        # evaluating these crops with season="Annual" and taking whichever
        # scores higher.
        self.annual_crops = {
            crop for crop, meta in self.crop_metadata.items() if "Annual" in meta.get("season", [])
        }
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

    def _agronomic_match(self, crop: str, numeric_row: dict) -> float:
        """
        Rule-based half of the suitability score: how closely the farmer's
        actual inputs sit to this crop's own empirical feature distribution
        (mean/std computed from that crop's real training rows — see
        crop_feature_stats in train_model.py), independent of anything the
        trained classifier "votes" for.

        Per-feature similarity is a Gaussian kernel centered on the crop's
        mean (1.0 = exactly typical, decaying with distance in standard
        deviations). Combined across features with a geometric mean rather
        than an average, deliberately: agronomically, a crop's suitability is
        limited by its worst-matched requirement, not softened by its best
        one (the same principle as Liebig's Law of the Minimum) — a
        catastrophic pH mismatch should tank the score even if nitrogen
        happens to be perfect.
        """
        stats = self.crop_feature_stats.get(crop)
        if not stats:
            return 0.5  # no stats available (shouldn't happen) — neutral, not fabricated high/low
        log_sims = []
        for feat in SUITABILITY_NUMERIC_FEATURES:
            if feat not in stats or feat not in numeric_row:
                continue
            mean, std = stats[feat]
            z = (numeric_row[feat] - mean) / std
            sim = np.exp(-0.5 * z * z)
            log_sims.append(np.log(max(sim, 1e-6)))
        if not log_sims:
            return 0.5
        return float(np.exp(np.mean(log_sims)))

    def predict(self, features: dict, season: str, location: str = "Karnataka") -> dict:
        row = {
            "N": features["nitrogen"],
            "P": features["phosphorus"],
            "K": features["potassium"],
            "temperature": features["temperature"],
            "humidity": features["humidity"],
            "ph": features["ph"],
            "rainfall": features["rainfall"],
            "moisture": features.get("moisture", 50.0),
            "season": self._safe_encode(self.season_encoder, season),
            "location": self._safe_encode(self.location_encoder, location or "Karnataka"),
        }
        X = pd.DataFrame([row])[self.feature_names]

        probabilities = self.model.predict_proba(X)[0]
        classes = self.label_encoder.classes_
        classifier_confidence = dict(zip(classes, probabilities.tolist()))
        model_scores = self._independent_confidences(X)

        # Second pass for Annual crops (see self.annual_crops) — score them
        # under season="Annual" too and keep whichever context they do
        # better under, since asking "how well does banana grow in Kharif"
        # is the wrong question for a crop that's actually grown year-round.
        if self.annual_crops and "Annual" in list(self.season_encoder.classes_):
            row_annual = {**row, "season": self._safe_encode(self.season_encoder, "Annual")}
            X_annual = pd.DataFrame([row_annual])[self.feature_names]
            classifier_confidence_annual = dict(zip(classes, self.model.predict_proba(X_annual)[0].tolist()))
            model_scores_annual = self._independent_confidences(X_annual)
            for crop in self.annual_crops:
                if crop in classifier_confidence_annual:
                    classifier_confidence[crop] = max(classifier_confidence[crop], classifier_confidence_annual[crop])
                if crop in model_scores_annual:
                    model_scores[crop] = max(model_scores.get(crop, 0.0), model_scores_annual[crop])

        numeric_row = {
            "N": features["nitrogen"], "P": features["phosphorus"], "K": features["potassium"],
            "temperature": features["temperature"], "humidity": features["humidity"],
            "ph": features["ph"], "rainfall": features["rainfall"],
            "moisture": features.get("moisture", 50.0),
        }

        # Suitability score = equal-weight blend of the trained model's
        # per-crop signal and a rule-based agronomic match against that
        # crop's own real feature distribution — "together with rule-based
        # agronomic validation", not the model probability alone. This also
        # keeps a strong-but-not-top crop from being reported as a misleading
        # 1-5% (which the pure one-vs-rest score often did) when its actual
        # growing conditions are a reasonably good match.
        MODEL_WEIGHT = 0.5
        AGRONOMIC_WEIGHT = 0.5
        suitability = {}
        for crop in classes:
            agronomic = self._agronomic_match(crop, numeric_row)
            suitability[crop] = MODEL_WEIGHT * model_scores.get(crop, 0.0) + AGRONOMIC_WEIGHT * agronomic

        ranked = sorted(suitability.items(), key=lambda kv: kv[1], reverse=True)

        # Always the top 6 by suitability — a confident, unambiguous
        # prediction is not a reason to show fewer than 6; the farmer still
        # benefits from seeing the next-best alternatives.
        MAX_RESULTS = 6
        top6 = ranked[:MAX_RESULTS]

        alternatives = [
            {
                "crop": crop, "confidence": round(float(score), 4),
                "suitability_tier": _suitability_tier(score),
                "crop_details": self.crop_metadata.get(crop, {}),
            }
            for crop, score in top6
        ]
        best_crop = top6[0][0]
        # "Prediction Confidence" reflects how sure the classifier is that
        # best_crop specifically is the single right answer among all 52
        # crops (a comparative, classification-style measure) — distinct from
        # best_crop's own blended suitability score shown on its card.
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
            "model_selected": self.metrics.get("model_selected"),
        }


_predictor: CropPredictor | None = None


def get_crop_predictor() -> CropPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CropPredictor()
    return _predictor
