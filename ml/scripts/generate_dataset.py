"""
Generates datasets/crop_recommendation.csv

For the 22 crops covered by the well-known public "Crop Recommendation
Dataset" (2200 rows of real N/P/K/temperature/humidity/ph/rainfall
measurements; see datasets/real_sources/CREDITS.md for provenance), those
real rows are used directly as ground truth. For the remaining 30 crops not
covered by that dataset, rows are synthetically generated from published
agronomic reference ranges (FAO / ICAR advisories), each crop modeled as a
multivariate Gaussian over its reference range and clipped to physically
valid bounds — documented as synthetic-but-realistic, not scraped or
measured data, so the exact provenance of every row is known.

Neither source includes `season`, `location`, or `moisture` columns (all
three are real predictive features in HealTheCrop's model), so all three are
added on top of both the real and synthetic rows:
  - `season`: each crop's known cultivation season — a fixed agronomic fact.
  - `location`: sampled via CROP_REGIONAL_AFFINITY-weighted choice so the
    state a farmer selects carries genuine signal (see comment below).
  - `moisture`: derived from each crop's own humidity/rainfall requirements
    (see `_derive_moisture_profile`) plus per-row noise — a standard
    agronomic proxy used because no public dataset here includes directly
    measured soil moisture.
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
SAMPLES_PER_CROP = 150
REAL_DATASET_PATH = Path(__file__).resolve().parents[2] / "datasets" / "real_sources" / "crop_recommendation_public_22crops.csv"


def _derive_moisture_profile(humidity: tuple, rainfall: tuple) -> tuple:
    """
    No dataset used here includes directly measured soil moisture, so it's
    approximated from each crop's own humidity + rainfall requirements —
    crops needing more atmospheric humidity and rainfall are grown in wetter
    soil. This is a standard agronomic proxy, computed the same documented
    way for every crop rather than invented by hand per crop.
    """
    humidity_mean, humidity_std = humidity
    rainfall_mean, _ = rainfall
    rainfall_norm = min(rainfall_mean / 250 * 100, 100)
    mean = round(0.6 * humidity_mean + 0.4 * rainfall_norm, 1)
    std = round(max(4.0, 0.5 * humidity_std), 1)
    return mean, std


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

# Crops covered by the real public dataset (datasets/real_sources/) — their
# N/P/K/temperature/humidity/ph/rainfall come from real measurements, not
# the Gaussian profiles above. The profiles above are still used for these
# crops' `moisture` derivation (see _derive_moisture_profile) since even the
# real dataset doesn't include soil moisture.
REAL_DATA_CROPS = {
    "rice", "maize", "chickpea", "kidneybeans", "pigeonpeas", "mothbeans",
    "mungbean", "blackgram", "lentil", "pomegranate", "banana", "mango",
    "grapes", "watermelon", "muskmelon", "apple", "orange", "papaya",
    "coconut", "cotton", "jute", "coffee",
}

MOISTURE_PROFILES = {
    crop: _derive_moisture_profile(profile["humidity"], profile["rainfall"])
    for crop, profile in CROP_PROFILES.items()
}

BOUNDS = dict(
    N=(0, 150), P=(0, 150), K=(0, 210),
    temperature=(5, 45), humidity=(10, 100),
    ph=(3.5, 9.5), rainfall=(15, 300), moisture=(5, 100),
)

LOCATIONS = [
    "Karnataka", "Tamil Nadu", "Kerala", "Andhra Pradesh", "Telangana",
    "Maharashtra", "Punjab", "Uttar Pradesh", "Madhya Pradesh", "West Bengal",
]

# States where each crop is a genuinely common regional match (broad, well-known
# agricultural geography — e.g. coconut/pepper on the Kerala/coastal Karnataka
# belt, wheat/mustard in the Punjab-UP belt, rice in West Bengal/Andhra Pradesh).
# Without this, `location` was assigned uniformly at random and carried zero
# correlation with the label, so the trained model learned to ignore it — the
# state dropdown had no real effect on predictions. Rows are still sampled
# outside this list some of the time (AFFINITY_WEIGHT below) so the model
# doesn't overfit to only these states and still handles the others sensibly.
CROP_REGIONAL_AFFINITY = {
    "rice": ["West Bengal", "Andhra Pradesh", "Tamil Nadu", "Punjab"],
    "maize": ["Karnataka", "Andhra Pradesh", "Madhya Pradesh"],
    "chickpea": ["Madhya Pradesh", "Maharashtra", "Uttar Pradesh"],
    "kidneybeans": ["Uttar Pradesh", "Madhya Pradesh"],
    "pigeonpeas": ["Maharashtra", "Karnataka", "Madhya Pradesh", "Uttar Pradesh"],
    "mothbeans": ["Maharashtra", "Karnataka"],
    "mungbean": ["Maharashtra", "Andhra Pradesh", "Madhya Pradesh"],
    "blackgram": ["Andhra Pradesh", "Tamil Nadu", "Maharashtra"],
    "lentil": ["Uttar Pradesh", "Madhya Pradesh", "West Bengal"],
    "pomegranate": ["Maharashtra", "Karnataka"],
    "banana": ["Tamil Nadu", "Maharashtra", "Andhra Pradesh", "Karnataka"],
    "mango": ["Andhra Pradesh", "Uttar Pradesh", "Karnataka", "Maharashtra"],
    "grapes": ["Maharashtra", "Karnataka"],
    "watermelon": ["Andhra Pradesh", "Karnataka", "Uttar Pradesh"],
    "muskmelon": ["Uttar Pradesh", "Andhra Pradesh", "Punjab"],
    "apple": [],  # no strong match among these 10 states (grown in HP/J&K/Uttarakhand)
    "orange": ["Maharashtra", "Madhya Pradesh"],
    "papaya": ["Andhra Pradesh", "Karnataka", "Tamil Nadu"],
    "coconut": ["Kerala", "Tamil Nadu", "Karnataka", "Andhra Pradesh"],
    "cotton": ["Maharashtra", "Telangana", "Punjab"],
    "jute": ["West Bengal"],
    "coffee": ["Karnataka", "Kerala", "Tamil Nadu"],
    "wheat": ["Punjab", "Uttar Pradesh", "Madhya Pradesh"],
    "sugarcane": ["Uttar Pradesh", "Maharashtra"],
    "tea": ["West Bengal", "Kerala"],
    "groundnut": ["Andhra Pradesh", "Tamil Nadu", "Karnataka"],
    "soybean": ["Madhya Pradesh", "Maharashtra"],
    "mustard": ["Uttar Pradesh", "Madhya Pradesh", "West Bengal", "Punjab"],
    "sunflower": ["Karnataka", "Andhra Pradesh", "Maharashtra"],
    "tomato": ["Andhra Pradesh", "Karnataka", "Maharashtra"],
    "onion": ["Maharashtra", "Karnataka", "Madhya Pradesh"],
    "potato": ["Uttar Pradesh", "West Bengal", "Punjab"],
    "garlic": ["Madhya Pradesh", "Uttar Pradesh"],
    "brinjal": ["West Bengal", "Andhra Pradesh", "Karnataka"],
    "cabbage": ["West Bengal", "Uttar Pradesh"],
    "cauliflower": ["West Bengal", "Uttar Pradesh"],
    "okra": ["Uttar Pradesh", "West Bengal", "Andhra Pradesh"],
    "spinach": ["Uttar Pradesh", "West Bengal"],
    "cucumber": ["Karnataka", "Maharashtra"],
    "guava": ["Uttar Pradesh", "Madhya Pradesh"],
    "turmeric": ["Telangana", "Andhra Pradesh", "Tamil Nadu", "Karnataka"],
    "ginger": ["Kerala", "Karnataka"],
    "blackpepper": ["Kerala", "Karnataka"],
    "cardamom": ["Kerala", "Karnataka", "Tamil Nadu"],
    "coriander": ["Madhya Pradesh", "Andhra Pradesh", "Karnataka"],
    "fenugreek": ["Madhya Pradesh", "Uttar Pradesh"],
    "sorghum": ["Maharashtra", "Karnataka", "Madhya Pradesh"],
    "pearlmillet": ["Maharashtra", "Uttar Pradesh"],
    "fingermillet": ["Karnataka", "Tamil Nadu", "Andhra Pradesh"],
    "carrot": ["Punjab", "Uttar Pradesh", "Karnataka"],
    "peas": ["Uttar Pradesh", "Madhya Pradesh", "Punjab"],
    "sesame": ["Madhya Pradesh", "Andhra Pradesh", "Karnataka", "Tamil Nadu"],
}

# Fraction of rows drawn from the crop's affinity states rather than uniformly
# from all ten — high enough to give the model real location signal, not so
# high that unlisted states become impossible outcomes.
AFFINITY_WEIGHT = 0.7


def _sample_location(rng: np.random.Generator, crop: str) -> str:
    affinity = CROP_REGIONAL_AFFINITY.get(crop) or []
    if affinity and rng.random() < AFFINITY_WEIGHT:
        return rng.choice(affinity)
    return rng.choice(LOCATIONS)


def _sample_moisture(rng: np.random.Generator, crop: str) -> float:
    mean, std = MOISTURE_PROFILES[crop]
    lo, hi = BOUNDS["moisture"]
    return float(np.clip(rng.normal(mean, std), lo, hi))


def _load_real_rows(rng: np.random.Generator) -> pd.DataFrame:
    if not REAL_DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Real dataset not found at {REAL_DATASET_PATH}. See "
            "datasets/real_sources/CREDITS.md for how to obtain it."
        )
    real = pd.read_csv(REAL_DATASET_PATH)
    real = real.dropna()  # the source is already clean, but never trust blindly
    rows = []
    for _, r in real.iterrows():
        crop = r["label"]
        if crop not in CROP_PROFILES:
            continue  # keep only crops HealTheCrop knows metadata for
        rows.append({
            "N": float(r["N"]), "P": float(r["P"]), "K": float(r["K"]),
            "temperature": float(r["temperature"]), "humidity": float(r["humidity"]),
            "ph": float(r["ph"]), "rainfall": float(r["rainfall"]),
            "moisture": _sample_moisture(rng, crop),
            "season": CROP_PROFILES[crop]["season"],
            "location": _sample_location(rng, crop),
            "label": crop,
            "data_source": "real",
        })
    return pd.DataFrame(rows)


def _generate_synthetic_rows(rng: np.random.Generator, samples_per_crop: int) -> pd.DataFrame:
    rows = []
    for crop, profile in CROP_PROFILES.items():
        if crop in REAL_DATA_CROPS:
            continue  # covered by the real dataset instead
        for _ in range(samples_per_crop):
            row = {"label": crop, "season": profile["season"], "data_source": "synthetic"}
            for feat in ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]:
                mean, std = profile[feat]
                value = rng.normal(mean, std)
                lo, hi = BOUNDS[feat]
                row[feat] = float(np.clip(value, lo, hi))
            row["moisture"] = _sample_moisture(rng, crop)
            row["location"] = _sample_location(rng, crop)
            rows.append(row)
    return pd.DataFrame(rows)


def generate(seed: int = SEED, samples_per_crop: int = SAMPLES_PER_CROP) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    real_df = _load_real_rows(rng)
    synthetic_df = _generate_synthetic_rows(rng, samples_per_crop)
    df = pd.concat([real_df, synthetic_df], ignore_index=True)

    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    for col in ["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "moisture"]:
        df[col] = df[col].round(2)
    return df[["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "moisture", "season", "location", "label", "data_source"]]


if __name__ == "__main__":
    out_path = Path(__file__).resolve().parents[2] / "datasets" / "crop_recommendation.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(out_path, index=False)
    n_real = (df["data_source"] == "real").sum()
    n_synthetic = (df["data_source"] == "synthetic").sum()
    print(f"Wrote {len(df)} rows across {df['label'].nunique()} crops to {out_path}")
    print(f"  {n_real} rows from the real public dataset ({len(REAL_DATA_CROPS)} crops)")
    print(f"  {n_synthetic} rows synthetically generated ({df['label'].nunique() - len(REAL_DATA_CROPS)} crops)")
