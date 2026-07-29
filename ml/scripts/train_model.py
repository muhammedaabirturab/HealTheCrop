"""
Trains the HealTheCrop Random Forest crop-recommendation model.

Reads datasets/crop_recommendation.csv, tunes hyperparameters via stratified
cross-validated random search, evaluates the best estimator on a held-out test
split, and serializes the fitted pipeline (model + label encoder + season/
location encoders + feature metadata + honest evaluation metrics) to
ml/models/crop_model.joblib so the FastAPI backend can load it directly.

"Model Accuracy" as shown in the app is this script's held-out test accuracy —
never a hand-picked or inflated number. Cross-validation is used only to select
hyperparameters, not to report the headline metric, so it can't overstate
real-world performance.

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
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "datasets" / "crop_recommendation.csv"
MODEL_DIR = ROOT / "ml" / "models"
NUMERIC_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
CATEGORICAL_FEATURES = ["season", "location"]

PARAM_DISTRIBUTIONS = {
    "n_estimators": [200, 300, 400, 500, 600],
    "max_depth": [None, 12, 16, 20, 24, 30],
    "min_samples_split": [2, 3, 4, 5],
    "min_samples_leaf": [1, 2, 3],
    "max_features": ["sqrt", "log2", None],
}


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

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    search = RandomizedSearchCV(
        estimator=RandomForestClassifier(random_state=42, class_weight="balanced", n_jobs=-1),
        param_distributions=PARAM_DISTRIBUTIONS,
        n_iter=25,
        cv=cv,
        scoring="accuracy",
        random_state=42,
        n_jobs=-1,
        refit=True,
    )
    print("Running randomized hyperparameter search with 5-fold cross-validation...")
    search.fit(X_train, y_train)
    model = search.best_estimator_

    print(f"Best CV accuracy: {search.best_score_:.4f}")
    print(f"Best params: {json.dumps(search.best_params_, indent=2)}")

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")
    report = classification_report(
        y_test, y_pred, target_names=label_encoder.classes_, output_dict=True, zero_division=0
    )

    print(f"Held-out test accuracy: {accuracy:.4f}")
    print(f"Held-out weighted F1: {f1:.4f}")

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
        "metrics": {
            "accuracy": accuracy,
            "weighted_f1": f1,
            "cv_mean_accuracy": float(search.best_score_),
            "cv_folds": cv.get_n_splits(),
        },
        "feature_importances": importances,
        "best_params": search.best_params_,
    }
    model_path = MODEL_DIR / "crop_model.joblib"
    joblib.dump(bundle, model_path)
    print(f"Saved model bundle to {model_path}")

    metrics_path = MODEL_DIR / "training_report.json"
    metrics_path.write_text(json.dumps({
        "accuracy": accuracy,
        "weighted_f1": f1,
        "cv_mean_accuracy": float(search.best_score_),
        "cv_folds": cv.get_n_splits(),
        "best_params": search.best_params_,
        "feature_importances": importances,
        "classification_report": report,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_classes": len(label_encoder.classes_),
        "classes": label_encoder.classes_.tolist(),
    }, indent=2))
    print(f"Saved training report to {metrics_path}")


if __name__ == "__main__":
    train()
