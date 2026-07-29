"""
Agronomic sanity check for the trained crop recommendation model.

Unlike train_model.py's held-out accuracy metric (which measures fit against the
synthetic training distribution), this script hand-picks realistic real-world input
combinations for specific known crops and checks that the model's top prediction
matches domain expectations. It's a regression check against agronomic plausibility,
not a formal accuracy benchmark - run it after any retraining to catch regressions
that a plain accuracy number could hide (e.g. a model that's 96% accurate on paper
but recommends coconut for a Rabi wheat-belt field).

Usage:
    python ml/scripts/sanity_check.py
"""
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "ml" / "models" / "crop_model.joblib"

# (description, features, expected_top_crop)
CASES = [
    (
        "West Bengal Kharif rice paddy - high N, high humidity, heavy monsoon rainfall",
        {"N": 95, "P": 45, "K": 42, "temperature": 26, "humidity": 85, "ph": 6.0, "rainfall": 250, "season": "Kharif", "location": "West Bengal"},
        "rice",
    ),
    (
        "Rabi chickpea - low N, high P/K, cool dry winter conditions",
        {"N": 35, "P": 68, "K": 78, "temperature": 19, "humidity": 16, "ph": 7.4, "rainfall": 70, "season": "Rabi", "location": "Madhya Pradesh"},
        "chickpea",
    ),
    (
        "Himalayan apple orchard - very high P/K, cold, high humidity",
        {"N": 18, "P": 130, "K": 195, "temperature": 21, "humidity": 90, "ph": 5.8, "rainfall": 110, "season": "Rabi", "location": "Uttar Pradesh"},
        "apple",
    ),
    (
        "Coffee plantation - high N, moderate humidity, warm",
        {"N": 100, "P": 27, "K": 32, "temperature": 24, "humidity": 58, "ph": 6.9, "rainfall": 150, "season": "Annual", "location": "Karnataka"},
        "coffee",
    ),
    (
        "Black-cotton-soil Kharif cotton - high N, low K, moderate rainfall",
        {"N": 115, "P": 45, "K": 20, "temperature": 25, "humidity": 78, "ph": 6.8, "rainfall": 82, "season": "Kharif", "location": "Maharashtra"},
        "cotton",
    ),
    (
        "Zaid summer watermelon - sandy loam, low rainfall, high humidity",
        {"N": 100, "P": 18, "K": 48, "temperature": 26, "humidity": 84, "ph": 6.6, "rainfall": 48, "season": "Zaid", "location": "Andhra Pradesh"},
        "watermelon",
    ),
    (
        "Coastal coconut grove - high humidity, high rainfall, sandy soil",
        {"N": 20, "P": 17, "K": 32, "temperature": 27, "humidity": 95, "ph": 5.8, "rainfall": 175, "season": "Annual", "location": "Kerala"},
        "coconut",
    ),
    (
        "Grape vineyard - very high P/K, moderate everything else",
        {"N": 23, "P": 132, "K": 200, "temperature": 24, "humidity": 81, "ph": 6.0, "rainfall": 70, "season": "Annual", "location": "Maharashtra"},
        "grapes",
    ),
    (
        "Punjab Rabi wheat belt - high N, cool, moderate rainfall",
        {"N": 120, "P": 60, "K": 40, "temperature": 18, "humidity": 55, "ph": 6.5, "rainfall": 75, "season": "Rabi", "location": "Punjab"},
        "wheat",
    ),
    (
        "Uttar Pradesh sugarcane belt - very high N/K, warm, heavy irrigation",
        {"N": 150, "P": 60, "K": 120, "temperature": 28, "humidity": 75, "ph": 6.5, "rainfall": 150, "season": "Annual", "location": "Uttar Pradesh"},
        "sugarcane",
    ),
    (
        "Rabi potato field - very high N/K, cool, acidic soil",
        {"N": 120, "P": 80, "K": 120, "temperature": 18, "humidity": 70, "ph": 5.5, "rainfall": 60, "season": "Rabi", "location": "Uttar Pradesh"},
        "potato",
    ),
    (
        "Kharif groundnut - sandy loam, low N, warm",
        {"N": 25, "P": 50, "K": 50, "temperature": 27, "humidity": 65, "ph": 6.3, "rainfall": 70, "season": "Kharif", "location": "Andhra Pradesh"},
        "groundnut",
    ),
    (
        "Kerala cardamom hills - high rainfall, high humidity, acidic",
        {"N": 30, "P": 30, "K": 60, "temperature": 22, "humidity": 85, "ph": 5.8, "rainfall": 250, "season": "Annual", "location": "Kerala"},
        "cardamom",
    ),
]


def run():
    if not MODEL_PATH.exists():
        print(f"Model not found at {MODEL_PATH}. Run generate_dataset.py + train_model.py first.")
        sys.exit(1)

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    label_encoder = bundle["label_encoder"]
    season_encoder = bundle["season_encoder"]
    location_encoder = bundle["location_encoder"]
    feature_names = bundle["feature_names"]

    failures = 0
    for description, features, expected in CASES:
        row = {
            "N": features["N"], "P": features["P"], "K": features["K"],
            "temperature": features["temperature"], "humidity": features["humidity"],
            "ph": features["ph"], "rainfall": features["rainfall"],
            "season": int(season_encoder.transform([features["season"]])[0]),
            "location": int(location_encoder.transform([features["location"]])[0]),
        }
        X = pd.DataFrame([row])[feature_names]
        probs = model.predict_proba(X)[0]
        ranked = sorted(zip(label_encoder.classes_, probs), key=lambda x: x[1], reverse=True)
        top_crop, top_conf = ranked[0]

        status = "PASS" if top_crop == expected else "FAIL"
        if status == "FAIL":
            failures += 1
        top3 = ", ".join(f"{c}={p:.2f}" for c, p in ranked[:3])
        print(f"[{status}] {description}\n  expected={expected} got={top_crop} ({top_conf:.2%})  top3=[{top3}]\n")

    print(f"{len(CASES) - failures}/{len(CASES)} sanity cases matched expected crop.")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    run()
