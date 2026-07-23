"""
Trains the HealTheCrop Random Forest crop-recommendation model.

Reads datasets/crop_recommendation.csv, trains a RandomForestClassifier,
evaluates it on a held-out test split, and serializes the fitted pipeline
(model + label encoder + season/location encoders + feature metadata) to
ml/models/crop_model.joblib so the FastAPI backend can load it directly.

Usage:
    python ml/scripts/generate_dataset.py   # only needed once, or to regenerate
    python ml/scripts/train_model.py
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "datasets" / "crop_recommendation.csv"
MODEL_DIR = ROOT / "ml" / "models"
NUMERIC_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
CATEGORICAL_FEATURES = ["season", "location"]


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"{DATASET_PATH} not found. Run generate_dataset.py first, "
            "or place a real dataset with matching columns there."
        )
    return pd.read_csv(DATASET_PATH)


def train():
    df = load_dataset()

    season_encoder = LabelEncoder().fit(df["season"])
    location_encoder = LabelEncoder().fit(df["location"])
    label_encoder = LabelEncoder().fit(df["label"])

    X = pd.DataFrame({
        **{f: df[f] for f in NUMERIC_FEATURES},
        "season": season_encoder.transform(df["season"]),
        "location": location_encoder.transform(df["location"]),
    })
    y = label_encoder.transform(df["label"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        n_jobs=-1,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")
    report = classification_report(
        y_test, y_pred, target_names=label_encoder.classes_, output_dict=True, zero_division=0
    )

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Weighted F1: {f1:.4f}")

    feature_names = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    importances = dict(zip(feature_names, model.feature_importances_.round(4).tolist()))
    print("Feature importances:", json.dumps(importances, indent=2))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "label_encoder": label_encoder,
        "season_encoder": season_encoder,
        "location_encoder": location_encoder,
        "feature_names": feature_names,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "metrics": {"accuracy": accuracy, "weighted_f1": f1},
        "feature_importances": importances,
    }
    model_path = MODEL_DIR / "crop_model.joblib"
    joblib.dump(bundle, model_path)
    print(f"Saved model bundle to {model_path}")

    metrics_path = MODEL_DIR / "training_report.json"
    metrics_path.write_text(json.dumps({
        "accuracy": accuracy,
        "weighted_f1": f1,
        "feature_importances": importances,
        "classification_report": report,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "classes": label_encoder.classes_.tolist(),
    }, indent=2))
    print(f"Saved training report to {metrics_path}")


if __name__ == "__main__":
    train()
