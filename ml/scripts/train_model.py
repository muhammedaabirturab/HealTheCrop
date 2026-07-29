"""
Trains the HealTheCrop Random Forest crop-recommendation model.

Reads datasets/crop_recommendation.csv, splits it into train/validation/test
(70/15/15, stratified), tunes hyperparameters via cross-validated random
search on the training split only, sanity-checks on the validation split,
then evaluates the final estimator exactly once on the held-out test split —
the test set is never touched during tuning, so it can't overstate real-world
performance. Serializes the fitted pipeline (model + label encoder + season/
location encoders + feature metadata + honest evaluation metrics, including a
confusion matrix) to ml/models/crop_model.joblib so the FastAPI backend can
load it directly.

"Model Accuracy" as shown in the app is this script's held-out test accuracy —
never a hand-picked or inflated number.

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
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score,
    precision_score, recall_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "datasets" / "crop_recommendation.csv"
MODEL_DIR = ROOT / "ml" / "models"
NUMERIC_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "moisture"]
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

    # 70/15/15 train/validation/test, stratified so every crop is represented
    # proportionally in all three splits. Validation is a sanity check during
    # development; test is the untouched final number reported to the app.
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
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
    print("Running randomized hyperparameter search with 5-fold cross-validation (train split only)...")
    search.fit(X_train, y_train)
    model = search.best_estimator_

    print(f"Best CV accuracy (train split): {search.best_score_:.4f}")
    print(f"Best params: {json.dumps(search.best_params_, indent=2)}")

    val_accuracy = accuracy_score(y_val, model.predict(X_val))
    print(f"Validation accuracy (sanity check, not the reported metric): {val_accuracy:.4f}")

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")
    precision_macro = precision_score(y_test, y_pred, average="macro", zero_division=0)
    recall_macro = recall_score(y_test, y_pred, average="macro", zero_division=0)
    report = classification_report(
        y_test, y_pred, target_names=label_encoder.classes_, output_dict=True, zero_division=0
    )
    conf_matrix = confusion_matrix(y_test, y_pred, labels=range(len(label_encoder.classes_)))

    print(f"Held-out TEST accuracy: {accuracy:.4f}")
    print(f"Held-out TEST weighted F1: {f1:.4f}")
    print(f"Held-out TEST macro precision: {precision_macro:.4f}")
    print(f"Held-out TEST macro recall: {recall_macro:.4f}")

    feature_names = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    importances = dict(zip(feature_names, model.feature_importances_.round(4).tolist()))
    print("Feature importances:", json.dumps(importances, indent=2))

    # The multiclass model above answers "which single crop fits best?" — its
    # probabilities are relative (they sum to 100% across all crops), which is
    # correct for picking a winner but wrong for per-crop "confidence" cards:
    # a second crop can only look bad because the top one looks good, not
    # because it's actually unsuitable. A one-vs-rest ensemble of independent
    # binary classifiers (this crop vs. everything else) gives each crop its
    # own 0-100% suitability score with no such coupling, reusing the same
    # tuned hyperparameters found above.
    print("Training one-vs-rest classifiers for independent per-crop confidence...")
    ovr_model = OneVsRestClassifier(
        RandomForestClassifier(random_state=42, class_weight="balanced", n_jobs=-1, **search.best_params_)
    )
    ovr_model.fit(X_train, y_train)
    print(f"Trained {len(ovr_model.estimators_)} independent one-vs-rest classifiers.")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": model,
        "ovr_model": ovr_model,
        "label_encoder": label_encoder,
        "season_encoder": season_encoder,
        "location_encoder": location_encoder,
        "feature_names": feature_names,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "metrics": {
            "accuracy": accuracy,
            "weighted_f1": f1,
            "precision_macro": precision_macro,
            "recall_macro": recall_macro,
            "validation_accuracy": val_accuracy,
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
        "precision_macro": precision_macro,
        "recall_macro": recall_macro,
        "validation_accuracy": val_accuracy,
        "cv_mean_accuracy": float(search.best_score_),
        "cv_folds": cv.get_n_splits(),
        "best_params": search.best_params_,
        "feature_importances": importances,
        "classification_report": report,
        "confusion_matrix": conf_matrix.tolist(),
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_test": len(X_test),
        "n_classes": len(label_encoder.classes_),
        "classes": label_encoder.classes_.tolist(),
    }, indent=2))
    print(f"Saved training report to {metrics_path}")


if __name__ == "__main__":
    train()
