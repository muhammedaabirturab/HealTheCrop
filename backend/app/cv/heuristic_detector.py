"""
Color/blob-based leaf symptom analyzer.

This is the zero-dependency, always-available detection path: it works the
moment the backend starts, without needing a trained CNN or GPU. It segments
an uploaded leaf image in HSV space into healthy-green / chlorotic-yellow /
necrotic-brown / black-spot regions, finds connected components ("lesions")
in the unhealthy masks, and maps the dominant symptom pattern + lesion count
onto plausible entries in the disease knowledge base.

It is intentionally conservative: this is a heuristic screening tool, not a
diagnostic replacement for the trained CNN (see disease_service.py, which
prefers cv/models/plant_disease_model.h5 when present and only falls back to
this module otherwise).
"""
from dataclasses import dataclass

import cv2
import numpy as np

# HSV ranges (OpenCV: H 0-179, S/V 0-255)
HEALTHY_GREEN = ((35, 40, 40), (85, 255, 255))
CHLOROTIC_YELLOW = ((20, 40, 100), (34, 255, 255))
NECROTIC_BROWN = ((5, 40, 20), (19, 255, 200))
BLACK_SPOT = ((0, 0, 0), (179, 100, 60))

MIN_LESION_AREA = 40


@dataclass
class LesionRegion:
    area_fraction: float
    bounding_box: tuple
    symptom: str


@dataclass
class HeuristicResult:
    healthy_fraction: float
    symptom_fractions: dict
    lesions: list
    dominant_symptom: str
    severity: str


def _mask_fraction(hsv: np.ndarray, lo: tuple, hi: tuple) -> tuple:
    mask = cv2.inRange(hsv, np.array(lo), np.array(hi))
    return mask, float(np.count_nonzero(mask)) / mask.size


def _find_lesions(mask: np.ndarray, symptom: str, total_pixels: int) -> list:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    lesions = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < MIN_LESION_AREA:
            continue
        x, y, w, h = cv2.boundingRect(c)
        lesions.append(LesionRegion(
            area_fraction=round(area / total_pixels, 4),
            bounding_box=(x, y, w, h),
            symptom=symptom,
        ))
    return lesions


def analyze(image_bgr: np.ndarray) -> HeuristicResult:
    image_bgr = cv2.resize(image_bgr, (512, 512))
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    total_pixels = hsv.shape[0] * hsv.shape[1]

    green_mask, green_frac = _mask_fraction(hsv, *HEALTHY_GREEN)
    yellow_mask, yellow_frac = _mask_fraction(hsv, *CHLOROTIC_YELLOW)
    brown_mask, brown_frac = _mask_fraction(hsv, *NECROTIC_BROWN)
    black_mask, black_frac = _mask_fraction(hsv, *BLACK_SPOT)

    lesions = (
        _find_lesions(yellow_mask, "chlorotic_yellow", total_pixels)
        + _find_lesions(brown_mask, "necrotic_brown", total_pixels)
        + _find_lesions(black_mask, "black_spot", total_pixels)
    )
    lesions.sort(key=lambda lesion: lesion.area_fraction, reverse=True)

    symptom_fractions = {
        "healthy_green": round(green_frac, 4),
        "chlorotic_yellow": round(yellow_frac, 4),
        "necrotic_brown": round(brown_frac, 4),
        "black_spot": round(black_frac, 4),
    }
    unhealthy_total = yellow_frac + brown_frac + black_frac
    dominant_symptom = max(
        ["chlorotic_yellow", "necrotic_brown", "black_spot"],
        key=lambda k: symptom_fractions[k],
    ) if unhealthy_total > 0.02 else "healthy_green"

    if unhealthy_total < 0.03:
        severity = "healthy"
    elif unhealthy_total < 0.12:
        severity = "mild"
    elif unhealthy_total < 0.30:
        severity = "moderate"
    else:
        severity = "severe"

    return HeuristicResult(
        healthy_fraction=round(green_frac, 4),
        symptom_fractions=symptom_fractions,
        lesions=lesions[:5],
        dominant_symptom=dominant_symptom,
        severity=severity,
    )


SYMPTOM_TO_CANDIDATES = {
    "chlorotic_yellow": [
        "General___Aphids", "General___Whitefly", "Deficiency___Nitrogen",
        "Deficiency___Iron", "Tomato___Leaf_curl_Tomato_leaf_curl_virus", "Okra___Yellow_vein_mosaic_disease",
    ],
    "necrotic_brown": [
        "Tomato___Early_blight", "Potato___Early_blight", "Maize___Turcicum_leaf_blight_TLB",
        "Groundnut___Leaf_spot_Early_Late_Leaf_Spot", "Deficiency___Potassium", "Wheat___Helminthosporium_leaf_blotch_Spot_blotch",
    ],
    "black_spot": [
        "Mango___Anthracnose", "Grapes___Anthracnose", "Rice___Rice_blast",
        "Citrus___Citrus_canker", "Chilli___Die_back_and_fruit_rot_anthracnose", "Sugarcane___Smut",
    ],
    "healthy_green": ["Healthy"],
}
