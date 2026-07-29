"""
Generates datasets/crop_recommendation.csv

HealTheCrop ships with a synthetically generated crop-recommendation dataset
built from published agronomic reference ranges (N-P-K requirements, temperature,
humidity, pH and rainfall tolerance per crop) rather than a scraped third-party
file, so the exact provenance and license of every row is known.

Each crop is modeled as a multivariate Gaussian over its agronomic reference
range, sampled `SAMPLES_PER_CROP` times, then clipped to physically valid
bounds. This keeps the class-conditional structure realistic enough for a
Random Forest to learn meaningful decision boundaries and feature importances,
while remaining fully reproducible (fixed seed) and free of external
dependencies at build time.

To use a real-world dataset instead (e.g. the public Kaggle
"Crop Recommendation Dataset"), simply drop a CSV with the same columns
(N, P, K, temperature, humidity, ph, rainfall, season, label) into
datasets/crop_recommendation.csv and skip this script.
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
SAMPLES_PER_CROP = 150

# (N, P, K, temperature C, humidity %, ph, rainfall mm) -> (mean, std) per crop
# Ranges are informed by FAO / ICAR agronomic advisories for these crops.
CROP_PROFILES = {
    "rice":        dict(N=(90, 15), P=(45, 10), K=(40, 10), temperature=(25, 3), humidity=(82, 5), ph=(6.2, 0.4), rainfall=(230, 40), season="Kharif"),
    "maize":       dict(N=(80, 15), P=(40, 10), K=(20, 8),  temperature=(24, 4), humidity=(63, 8), ph=(6.1, 0.5), rainfall=(85, 25),  season="Kharif"),
    "chickpea":    dict(N=(40, 10), P=(65, 12), K=(80, 12), temperature=(20, 4), humidity=(17, 6), ph=(7.3, 0.5), rainfall=(75, 20),  season="Rabi"),
    "kidneybeans": dict(N=(20, 8),  P=(65, 12), K=(20, 8),  temperature=(18, 3), humidity=(21, 6), ph=(5.8, 0.5), rainfall=(105, 20), season="Kharif"),
    "pigeonpeas":  dict(N=(20, 8),  P=(65, 12), K=(20, 8),  temperature=(27, 4), humidity=(48, 10),ph=(5.8, 0.5), rainfall=(150, 30), season="Kharif"),
    "mothbeans":   dict(N=(20, 8),  P=(45, 10), K=(20, 8),  temperature=(28, 3), humidity=(53, 10),ph=(6.8, 0.5), rainfall=(50, 15),  season="Kharif"),
    "mungbean":    dict(N=(20, 8),  P=(47, 10), K=(20, 8),  temperature=(28, 3), humidity=(85, 5), ph=(6.7, 0.5), rainfall=(50, 15),  season="Kharif"),
    "blackgram":   dict(N=(40, 8),  P=(65, 12), K=(20, 8),  temperature=(29, 3), humidity=(65, 8), ph=(7.1, 0.5), rainfall=(70, 15),  season="Kharif"),
    "lentil":      dict(N=(20, 8),  P=(68, 12), K=(20, 8),  temperature=(19, 3), humidity=(65, 8), ph=(6.9, 0.5), rainfall=(45, 15),  season="Rabi"),
    "pomegranate": dict(N=(19, 8),  P=(18, 8),  K=(40, 10), temperature=(21, 3), humidity=(90, 4), ph=(6.4, 0.5), rainfall=(105, 20), season="Annual"),
    "banana":      dict(N=(100, 15),P=(82, 12), K=(50, 12), temperature=(27, 3), humidity=(80, 5), ph=(5.9, 0.4), rainfall=(105, 25), season="Annual"),
    "mango":       dict(N=(20, 8),  P=(27, 8),  K=(30, 10), temperature=(31, 3), humidity=(50, 8), ph=(5.7, 0.5), rainfall=(95, 20),  season="Annual"),
    "grapes":      dict(N=(23, 8),  P=(132, 15),K=(200, 15),temperature=(24, 4), humidity=(81, 5), ph=(6.0, 0.4), rainfall=(70, 15),  season="Annual"),
    "watermelon":  dict(N=(100, 15),P=(17, 8),  K=(50, 10), temperature=(25, 3), humidity=(85, 5), ph=(6.5, 0.4), rainfall=(50, 15),  season="Zaid"),
    "muskmelon":   dict(N=(100, 15),P=(17, 8),  K=(50, 10), temperature=(28, 3), humidity=(92, 4), ph=(6.4, 0.4), rainfall=(25, 10),  season="Zaid"),
    "apple":       dict(N=(20, 8),  P=(134, 15),K=(200, 15),temperature=(22, 3), humidity=(92, 4), ph=(5.9, 0.4), rainfall=(112, 20), season="Rabi"),
    "orange":      dict(N=(19, 8),  P=(16, 8),  K=(10, 6),  temperature=(22, 3), humidity=(92, 4), ph=(6.4, 0.4), rainfall=(110, 20), season="Annual"),
    "papaya":      dict(N=(50, 12), P=(59, 12), K=(50, 12), temperature=(33, 3), humidity=(92, 4), ph=(6.7, 0.4), rainfall=(145, 25), season="Annual"),
    "coconut":     dict(N=(21, 8),  P=(16, 8),  K=(30, 10), temperature=(27, 2), humidity=(94, 3), ph=(5.9, 0.4), rainfall=(175, 25), season="Annual"),
    "cotton":      dict(N=(117, 15),P=(46, 10), K=(19, 8),  temperature=(24, 3), humidity=(80, 5), ph=(6.9, 0.5), rainfall=(80, 20),  season="Kharif"),
    "jute":        dict(N=(78, 12), P=(47, 10), K=(40, 10), temperature=(25, 2), humidity=(80, 4), ph=(6.7, 0.4), rainfall=(175, 25), season="Kharif"),
    "coffee":      dict(N=(101, 15),P=(28, 8),  K=(30, 10), temperature=(25, 3), humidity=(58, 8), ph=(6.8, 0.4), rainfall=(155, 25), season="Annual"),
    # Expansion set — cereals, oilseeds, vegetables, spices, millets, and cash
    # crops beyond the original 22, so the model has enough class diversity to
    # discriminate meaningfully across realistic manual-input ranges.
    "wheat":        dict(N=(120, 15), P=(60, 10), K=(40, 10),  temperature=(18, 3), humidity=(55, 8), ph=(6.5, 0.4), rainfall=(75, 20),  season="Rabi"),
    "sugarcane":    dict(N=(150, 15), P=(60, 10), K=(120, 15), temperature=(28, 3), humidity=(75, 6), ph=(6.5, 0.4), rainfall=(150, 25), season="Annual"),
    "tea":          dict(N=(90, 12),  P=(30, 8),  K=(60, 10),  temperature=(22, 3), humidity=(85, 5), ph=(5.0, 0.4), rainfall=(220, 30), season="Annual"),
    "groundnut":    dict(N=(25, 8),   P=(50, 10), K=(50, 10),  temperature=(27, 3), humidity=(65, 8), ph=(6.3, 0.4), rainfall=(70, 15),  season="Kharif"),
    "soybean":      dict(N=(30, 8),   P=(60, 10), K=(40, 10),  temperature=(26, 3), humidity=(70, 8), ph=(6.5, 0.4), rainfall=(90, 20),  season="Kharif"),
    "mustard":      dict(N=(80, 12),  P=(40, 10), K=(30, 8),   temperature=(20, 3), humidity=(50, 8), ph=(6.5, 0.4), rainfall=(40, 12),  season="Rabi"),
    "sunflower":    dict(N=(60, 10),  P=(60, 10), K=(40, 10),  temperature=(24, 3), humidity=(55, 8), ph=(6.8, 0.4), rainfall=(60, 15),  season="Zaid"),
    "tomato":       dict(N=(100, 12), P=(60, 10), K=(60, 10),  temperature=(24, 3), humidity=(65, 8), ph=(6.3, 0.4), rainfall=(60, 15),  season="Kharif"),
    "onion":        dict(N=(80, 10),  P=(40, 10), K=(60, 10),  temperature=(20, 3), humidity=(60, 8), ph=(6.3, 0.4), rainfall=(50, 12),  season="Rabi"),
    "potato":       dict(N=(120, 12), P=(80, 10), K=(120, 12), temperature=(18, 3), humidity=(70, 8), ph=(5.5, 0.4), rainfall=(60, 15),  season="Rabi"),
    "garlic":       dict(N=(75, 10),  P=(50, 10), K=(60, 10),  temperature=(17, 3), humidity=(55, 8), ph=(6.3, 0.4), rainfall=(45, 12),  season="Rabi"),
    "brinjal":      dict(N=(100, 12), P=(60, 10), K=(60, 10),  temperature=(26, 3), humidity=(65, 8), ph=(6.2, 0.4), rainfall=(70, 15),  season="Kharif"),
    "cabbage":      dict(N=(120, 12), P=(60, 10), K=(60, 10),  temperature=(18, 3), humidity=(70, 8), ph=(6.2, 0.4), rainfall=(55, 12),  season="Rabi"),
    "cauliflower":  dict(N=(120, 12), P=(70, 10), K=(70, 10),  temperature=(18, 3), humidity=(70, 8), ph=(6.2, 0.4), rainfall=(55, 12),  season="Rabi"),
    "okra":         dict(N=(80, 10),  P=(50, 10), K=(50, 10),  temperature=(28, 3), humidity=(65, 8), ph=(6.3, 0.4), rainfall=(70, 15),  season="Kharif"),
    "spinach":      dict(N=(90, 10),  P=(50, 10), K=(40, 10),  temperature=(20, 3), humidity=(60, 8), ph=(6.3, 0.4), rainfall=(50, 12),  season="Rabi"),
    "cucumber":     dict(N=(80, 10),  P=(50, 10), K=(40, 10),  temperature=(26, 3), humidity=(65, 8), ph=(6.3, 0.4), rainfall=(55, 12),  season="Zaid"),
    "guava":        dict(N=(20, 8),   P=(20, 8),  K=(30, 10),  temperature=(25, 3), humidity=(65, 8), ph=(6.5, 0.4), rainfall=(100, 20), season="Annual"),
    "turmeric":     dict(N=(60, 10),  P=(50, 10), K=(100, 12), temperature=(27, 3), humidity=(80, 6), ph=(6.0, 0.4), rainfall=(150, 25), season="Kharif"),
    "ginger":       dict(N=(60, 10),  P=(50, 10), K=(100, 12), temperature=(25, 3), humidity=(80, 6), ph=(6.0, 0.4), rainfall=(180, 25), season="Kharif"),
    "blackpepper":  dict(N=(40, 10),  P=(30, 8),  K=(60, 10),  temperature=(25, 3), humidity=(85, 5), ph=(5.8, 0.4), rainfall=(200, 25), season="Annual"),
    "cardamom":     dict(N=(30, 8),   P=(30, 8),  K=(60, 10),  temperature=(22, 3), humidity=(85, 5), ph=(5.8, 0.4), rainfall=(250, 30), season="Annual"),
    "coriander":    dict(N=(40, 10),  P=(30, 8),  K=(20, 8),   temperature=(22, 3), humidity=(55, 8), ph=(6.5, 0.4), rainfall=(45, 12),  season="Rabi"),
    "fenugreek":    dict(N=(30, 8),   P=(40, 10), K=(20, 8),   temperature=(20, 3), humidity=(50, 8), ph=(6.5, 0.4), rainfall=(40, 12),  season="Rabi"),
    "sorghum":      dict(N=(70, 10),  P=(35, 8),  K=(30, 8),   temperature=(28, 3), humidity=(55, 8), ph=(6.5, 0.4), rainfall=(65, 15),  season="Kharif"),
    "pearlmillet":  dict(N=(50, 10),  P=(30, 8),  K=(25, 8),   temperature=(30, 3), humidity=(45, 8), ph=(6.8, 0.4), rainfall=(45, 12),  season="Kharif"),
    "fingermillet": dict(N=(50, 10),  P=(30, 8),  K=(25, 8),   temperature=(24, 3), humidity=(60, 8), ph=(6.0, 0.4), rainfall=(80, 15),  season="Kharif"),
    "carrot":       dict(N=(70, 10),  P=(50, 10), K=(90, 12),  temperature=(18, 3), humidity=(60, 8), ph=(6.3, 0.4), rainfall=(50, 12),  season="Rabi"),
    "peas":         dict(N=(25, 8),   P=(60, 10), K=(40, 10),  temperature=(16, 3), humidity=(55, 8), ph=(6.5, 0.4), rainfall=(55, 12),  season="Rabi"),
    "sesame":       dict(N=(30, 8),   P=(30, 8),  K=(20, 8),   temperature=(28, 3), humidity=(50, 8), ph=(6.5, 0.4), rainfall=(50, 12),  season="Kharif"),
}

BOUNDS = dict(
    N=(0, 150), P=(0, 150), K=(0, 210),
    temperature=(5, 45), humidity=(10, 100),
    ph=(3.5, 9.5), rainfall=(15, 300),
)

LOCATIONS = [
    "Karnataka", "Tamil Nadu", "Kerala", "Andhra Pradesh", "Telangana",
    "Maharashtra", "Punjab", "Uttar Pradesh", "Madhya Pradesh", "West Bengal",
]


def generate(seed: int = SEED, samples_per_crop: int = SAMPLES_PER_CROP) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for crop, profile in CROP_PROFILES.items():
        for _ in range(samples_per_crop):
            row = {"label": crop, "season": profile["season"]}
            for feat in ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]:
                mean, std = profile[feat]
                value = rng.normal(mean, std)
                lo, hi = BOUNDS[feat]
                row[feat] = float(np.clip(value, lo, hi))
            row["location"] = rng.choice(LOCATIONS)
            rows.append(row)
    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    for col in ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]:
        df[col] = df[col].round(2)
    return df[["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "season", "location", "label"]]


if __name__ == "__main__":
    out_path = Path(__file__).resolve().parents[2] / "datasets" / "crop_recommendation.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows across {df['label'].nunique()} crops to {out_path}")
