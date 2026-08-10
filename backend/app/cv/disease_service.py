"""
Pest & disease detection service.

Prefers a trained EfficientNetB0 CNN (cv/models/plant_disease_model.h5,
produced by cv/scripts/train_disease_model.py) when present. If no trained
model has been placed there yet, transparently falls back to the OpenCV
color/blob heuristic in heuristic_detector.py so the endpoint is functional
out of the box without requiring a multi-GB image dataset download — see
docs/MODEL_TRAINING.md for why training wasn't run in this environment and
what's needed to do it.
"""
import json
import logging
from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings
from app.cv import heuristic_detector as heuristic
from app.cv import image_quality

logger = logging.getLogger(__name__)
settings = get_settings()
_BASE_DIR = Path(__file__).resolve().parents[2]  # backend/app/cv -> backend/

# Below this top-candidate confidence, tell the farmer the diagnosis is
# uncertain rather than presenting it as definitive — see disease_knowledge_base
# rebuild notes (task: confidence-based uncertainty messaging).
CONFIDENCE_UNCERTAIN_THRESHOLD = 0.45

SUPPORTED_LANGUAGES = {"en", "hi", "kn", "ta", "te", "ml"}

# Fields that carry a per-language translation under entry["translations"][lang].
# Scientific names, product/chemical names, and citations are intentionally
# excluded — see cv/data/translations/README.md.
TRANSLATABLE_FIELDS = [
    "display_name", "description", "organic_treatment", "biological_control",
    "chemical_treatment", "dosage_guidance", "safety_precautions",
    "waiting_period_before_harvest", "prevention_tips", "recovery_recommendations",
]


class DiseaseDetectionService:
    def __init__(self):
        self.knowledge_base = json.loads(
            (_BASE_DIR / settings.DISEASE_KB_PATH).resolve().read_text(encoding="utf-8")
        )
        self.cnn_model = None
        self.class_indices = None
        self._try_load_cnn()

    def _try_load_cnn(self):
        model_path = (_BASE_DIR / settings.DISEASE_MODEL_PATH).resolve()
        class_index_path = (_BASE_DIR / settings.DISEASE_CLASS_INDEX_PATH).resolve()
        if not model_path.exists() or not class_index_path.exists():
            logger.info("No trained CNN found at %s; using heuristic detector", model_path)
            return
        try:
            import tensorflow as tf
            self.cnn_model = tf.keras.models.load_model(model_path)
            self.class_indices = json.loads(class_index_path.read_text(encoding="utf-8"))
            logger.info("Loaded trained plant disease CNN from %s", model_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load CNN (%s); using heuristic detector", exc)
            self.cnn_model = None

    @property
    def model_used(self) -> str:
        return "cnn" if self.cnn_model is not None else "heuristic"

    def _kb_entry(self, key: str, lang: str = "en") -> dict:
        entry = self.knowledge_base.get(key, self.knowledge_base["Healthy"])
        result = {"name": key, **entry, "content_language": "en"}
        if lang != "en":
            localized = entry.get("translations", {}).get(lang)
            if localized:
                result.update({field: localized[field] for field in TRANSLATABLE_FIELDS if field in localized})
                result["content_language"] = lang
        return result

    def _predict_cnn(self, image_bgr: np.ndarray, lang: str) -> list[dict]:
        import tensorflow as tf
        img = cv2.resize(image_bgr, (224, 224))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        arr = tf.keras.applications.efficientnet.preprocess_input(img.astype("float32"))
        arr = np.expand_dims(arr, axis=0)
        preds = self.cnn_model.predict(arr, verbose=0)[0]
        top_indices = preds.argsort()[-3:][::-1]

        results = []
        for idx in top_indices:
            class_key = self.class_indices.get(str(idx), "Healthy")
            entry = self._kb_entry(class_key, lang)
            results.append({**entry, "confidence": round(float(preds[idx]), 4), "region": None})
        return results

    def _predict_heuristic(self, image_bgr: np.ndarray, lang: str) -> tuple[list[dict], str]:
        result = heuristic.analyze(image_bgr)
        if result.dominant_symptom == "healthy_green" or not result.lesions:
            return [{**self._kb_entry("Healthy", lang), "confidence": round(result.healthy_fraction, 4), "region": None}], result.severity

        # One symptom pattern maps to several plausible diagnoses, not several
        # lesions each independently re-picking the same top candidate — return
        # the top 3 distinct candidates for the dominant symptom (ranked, with
        # decreasing confidence) so the farmer sees 3 different possible
        # cures instead of the same one repeated for every detected lesion.
        candidates = heuristic.SYMPTOM_TO_CANDIDATES.get(result.dominant_symptom, ["Healthy"])
        primary_lesion = result.lesions[0]
        base_confidence = min(0.5 + primary_lesion.area_fraction * 3, 0.92)
        rank_decay = [1.0, 0.7, 0.5]

        detections = []
        for rank, candidate_key in enumerate(candidates[:3]):
            entry = self._kb_entry(candidate_key, lang)
            detections.append({
                **entry,
                "confidence": round(base_confidence * rank_decay[rank], 4),
                "region": list(primary_lesion.bounding_box) if rank == 0 else None,
            })
        severity = "mild" if result.severity == "healthy" else result.severity
        return detections, severity

    def detect(self, image_bytes: bytes, lang: str = "en") -> dict:
        lang = lang if lang in SUPPORTED_LANGUAGES else "en"
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise ValueError("Could not decode image. Please upload a valid JPEG/PNG file.")

        quality = image_quality.assess(image_bgr)
        if not quality.is_acceptable:
            return {
                "model_used": self.model_used,
                "detections": [],
                "severity": "unknown",
                "image_quality": {
                    "is_acceptable": False,
                    "issues": quality.issues,
                    "messages": [image_quality.ISSUE_MESSAGES[issue] for issue in quality.issues],
                },
                "is_uncertain": True,
                "uncertainty_note": "Image quality checks failed — upload a clearer photo instead of relying on this result.",
            }

        if self.cnn_model is not None:
            detections = self._predict_cnn(image_bgr, lang)
            severity = "severe" if detections[0]["confidence"] > 0.7 and detections[0]["name"] != "Healthy" else "mild"
        else:
            detections, severity = self._predict_heuristic(image_bgr, lang)

        top_confidence = detections[0]["confidence"] if detections else 0.0
        is_uncertain = top_confidence < CONFIDENCE_UNCERTAIN_THRESHOLD
        uncertainty_note = (
            "Confidence is low — this diagnosis is uncertain. Consider consulting a local "
            "agricultural extension officer or plant pathologist before applying treatment."
            if is_uncertain else None
        )

        return {
            "model_used": self.model_used,
            "detections": detections,
            "severity": severity,
            "image_quality": {"is_acceptable": True, "issues": [], "messages": []},
            "is_uncertain": is_uncertain,
            "uncertainty_note": uncertainty_note,
        }


_service: DiseaseDetectionService | None = None


def get_disease_service() -> DiseaseDetectionService:
    global _service
    if _service is None:
        _service = DiseaseDetectionService()
    return _service
