"""
Rule-based soil health scoring and fertility-improvement recommendation engine.
Reads thresholds/suggestions from ml/data/fertility_recommendations.json so
agronomy content can be updated without touching code.
"""
import json
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()
_BASE_DIR = Path(__file__).resolve().parents[2]  # backend/app/services -> backend/

IDEAL_RANGES = {
    "nitrogen": (40, 120),
    "phosphorus": (30, 100),
    "potassium": (30, 150),
    "ph": (6.0, 7.5),
    "moisture": (30, 70),
}


def _load_rules() -> dict:
    path = (_BASE_DIR / settings.FERTILITY_RULES_PATH).resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def _status_for(value: float, lo: float, hi: float) -> str:
    if value is None:
        return "unknown"
    span = hi - lo
    if lo <= value <= hi:
        return "excellent" if (hi - value) / span > 0.3 and (value - lo) / span > 0.3 else "good"
    deviation = min(abs(value - lo), abs(value - hi)) / span
    if deviation < 0.25:
        return "average"
    if deviation < 0.6:
        return "poor"
    return "critical"


def compute_soil_health(reading: dict) -> dict:
    indicators = {}
    for key, (lo, hi) in IDEAL_RANGES.items():
        value = reading.get(key)
        indicators[key] = {
            "value": value,
            "status": _status_for(value, lo, hi) if value is not None else "unknown",
            "ideal_range": [lo, hi],
        }

    status_scores = {"excellent": 100, "good": 80, "average": 60, "poor": 35, "critical": 10, "unknown": 50}
    scored = [status_scores[i["status"]] for i in indicators.values()]
    fertility_score = round(sum(scored) / len(scored), 1) if scored else 0.0

    return {"indicators": indicators, "fertility_score": fertility_score}


def generate_suggestions(reading: dict) -> list[dict]:
    rules = _load_rules()
    suggestions = []

    n, p, k = reading.get("nitrogen"), reading.get("phosphorus"), reading.get("potassium")
    ph, moisture = reading.get("ph"), reading.get("moisture")

    if n is not None and n < 40:
        suggestions.append(rules["nitrogen_low"])
    if p is not None and p < 30:
        suggestions.append(rules["phosphorus_low"])
    if k is not None and k < 30:
        suggestions.append(rules["potassium_low"])
    if ph is not None and ph < 5.5:
        suggestions.append(rules["ph_acidic"])
    if ph is not None and ph > 8.0:
        suggestions.append(rules["ph_alkaline"])
    if moisture is not None and moisture < 30:
        suggestions.append(rules["moisture_low"])
    if moisture is not None and moisture > 85:
        suggestions.append(rules["moisture_high"])

    if not suggestions:
        suggestions.append(rules["micronutrient_deficiency"])

    return suggestions
