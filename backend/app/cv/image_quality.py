"""
Pre-diagnosis image quality gate.

Runs cheap, single-pass checks before the image is handed to the disease
detector. Catches the failure modes that make any prediction (CNN or
heuristic) unreliable: blur, bad exposure, too-small images, and photos that
don't appear to contain plant material at all. When a check fails we tell the
farmer what's wrong instead of returning a guess built on unusable input.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

MIN_DIMENSION_PX = 128
BLUR_VARIANCE_THRESHOLD = 45.0
DARK_MEAN_THRESHOLD = 35.0
BRIGHT_MEAN_THRESHOLD = 235.0
MIN_PLANT_COLOR_FRACTION = 0.10

# Broad vegetation-like hue band covering healthy green through the
# yellow/brown tones of common leaf symptoms (OpenCV H range 0-179). The
# saturation floor of 45 is high enough to exclude desaturated/noisy neutral
# surfaces (walls, sky, skin) that would otherwise drift into this hue band.
_PLANT_HUE_LO = np.array((0, 45, 15))
_PLANT_HUE_HI = np.array((95, 255, 245))
# Necrotic/black-spot lesions are often low-saturation near-black, so they'd
# be missed by the saturation floor above — catch them via low brightness
# regardless of hue/saturation instead.
_DARK_LESION_LO = np.array((0, 0, 0))
_DARK_LESION_HI = np.array((179, 255, 70))


@dataclass
class ImageQualityResult:
    is_acceptable: bool
    issues: list = field(default_factory=list)
    blur_score: float = 0.0
    brightness: float = 0.0
    plant_color_fraction: float = 0.0


ISSUE_MESSAGES = {
    "low_resolution": "Image resolution is too small to analyze reliably. Please upload a larger photo.",
    "blurry": "Image appears blurry or out of focus. Please hold the camera steady and retake the photo.",
    "too_dark": "Image is too dark to analyze. Please retake the photo in better lighting.",
    "overexposed": "Image is overexposed (too bright/washed out). Please avoid direct glare and retake the photo.",
    "no_plant_detected": "This image doesn't appear to contain a plant leaf or crop. Please upload a clear photo of the affected plant.",
}


def assess(image_bgr: np.ndarray) -> ImageQualityResult:
    issues: list[str] = []
    height, width = image_bgr.shape[:2]

    if min(height, width) < MIN_DIMENSION_PX:
        issues.append("low_resolution")

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if blur_score < BLUR_VARIANCE_THRESHOLD:
        issues.append("blurry")

    brightness = float(gray.mean())
    if brightness < DARK_MEAN_THRESHOLD:
        issues.append("too_dark")
    elif brightness > BRIGHT_MEAN_THRESHOLD:
        issues.append("overexposed")

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    plant_mask = cv2.inRange(hsv, _PLANT_HUE_LO, _PLANT_HUE_HI)
    dark_lesion_mask = cv2.inRange(hsv, _DARK_LESION_LO, _DARK_LESION_HI)
    combined_mask = cv2.bitwise_or(plant_mask, dark_lesion_mask)
    plant_color_fraction = float(np.count_nonzero(combined_mask)) / combined_mask.size
    if plant_color_fraction < MIN_PLANT_COLOR_FRACTION:
        issues.append("no_plant_detected")

    return ImageQualityResult(
        is_acceptable=len(issues) == 0,
        issues=issues,
        blur_score=round(blur_score, 2),
        brightness=round(brightness, 2),
        plant_color_fraction=round(plant_color_fraction, 4),
    )
