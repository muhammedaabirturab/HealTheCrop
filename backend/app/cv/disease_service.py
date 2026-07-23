"""
Pest & disease detection service.

Prefers a trained MobileNetV2 CNN (cv/models/plant_disease_model.h5, produced
by cv/scripts/train_disease_model.py) when present. If no trained model has
been placed there yet, transparently falls back to the OpenCV color/blob
heuristic in heuristic_detector.py so the endpoint is functional out of the
box without requiring a multi-GB image dataset download.
"""
import json
import logging
from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings
from app.cv import heuristic_detector as heuristic

logger = logging.getLogger(__name__)
settings = get_settings()
_BASE_DIR = Path(__file__).resolve().parents[2]  # backend/app/cv -> backend/


class DiseaseDetectionService:
    def __init__(self):
        self.knowledge_base = json.loads(
            (_BASE_DIR / settings.DISEASE_KB_PATH).resolve().read_text()
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
            self.class_indices = json.loads(class_index_path.read_text())
            logger.info("Loaded trained plant disease CNN from %s", model_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load CNN (%s); using heuristic detector", exc)
            self.cnn_model = None

    @property
    def model_used(self) -> str:
        return "cnn" if self.cnn_model is not None else "heuristic"

    def _kb_entry(self, key: str) -> dict:
        entry = self.knowledge_base.get(key, self.knowledge_base["Healthy"])
        return {"name": key, **entry}

    def _predict_cnn(self, image_bgr: np.ndarray) -> list[dict]:
        import tensorflow as tf
        img = cv2.resize(image_bgr, (224, 224))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        arr = tf.keras.applications.mobilenet_v2.preprocess_input(img.astype("float32"))
        arr = np.expand_dims(arr, axis=0)
        preds = self.cnn_model.predict(arr, verbose=0)[0]
        top_indices = preds.argsort()[-3:][::-1]

        results = []
        for idx in top_indices:
            class_key = self.class_indices.get(str(idx), "Healthy")
            entry = self._kb_entry(class_key)
            results.append({**entry, "confidence": round(float(preds[idx]), 4), "region": None})
        return results

    def _predict_heuristic(self, image_bgr: np.ndarray) -> tuple[list[dict], str]:
        result = heuristic.analyze(image_bgr)
        if result.dominant_symptom == "healthy_green" or not result.lesions:
            return [{**self._kb_entry("Healthy"), "confidence": round(result.healthy_fraction, 4), "region": None}], result.severity

        candidates = heuristic.SYMPTOM_TO_CANDIDATES.get(result.dominant_symptom, ["Healthy"])
        detections = []
        for lesion in result.lesions:
            symptom_candidates = heuristic.SYMPTOM_TO_CANDIDATES.get(lesion.symptom, candidates)
            best_key = symptom_candidates[0]
            entry = self._kb_entry(best_key)
            detections.append({
                **entry,
                "confidence": round(min(0.5 + lesion.area_fraction * 3, 0.92), 4),
                "region": list(lesion.bounding_box),
            })
        severity = "mild" if result.severity == "healthy" else result.severity
        return detections, severity

    def detect(self, image_bytes: bytes) -> dict:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise ValueError("Could not decode image. Please upload a valid JPEG/PNG file.")

        if self.cnn_model is not None:
            detections = self._predict_cnn(image_bgr)
            severity = "severe" if detections[0]["confidence"] > 0.7 and detections[0]["name"] != "Healthy" else "mild"
        else:
            detections, severity = self._predict_heuristic(image_bgr)

        return {
            "model_used": self.model_used,
            "detections": detections,
            "severity": severity,
        }


_service: DiseaseDetectionService | None = None


def get_disease_service() -> DiseaseDetectionService:
    global _service
    if _service is None:
        _service = DiseaseDetectionService()
    return _service
