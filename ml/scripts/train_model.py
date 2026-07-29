"""
Trains the HealTheCrop crop-recommendation model.

Reads datasets/crop_recommendation.csv, splits it into train/validation/test
(70/15/15, stratified), tunes hyperparameters for two tree-ensemble families
(Random Forest and HistGradientBoosting — sklearn's fast, histogram-based
boosting implementation, comparable in approach to XGBoost/LightGBM) via
cross-validated random search on the training split only, compares both on
the validation split to pick a winner, then evaluates the winner exactly once
on the held-out test split — the test set is never touched during tuning or
model selection, so it can't overstate real-world performance.

Serializes the fitted pipeline (model + label encoder + season/location
encoders + feature metadata + per-crop empirical feature statistics used for
the rule-based half of the suitability score + honest evaluation metrics,
including a confusion matrix) to ml/models/crop_model.joblib, and writes a
feature-importance chart plus a full evaluation report.

"Model Accuracy" as shown in the app is this script's held-out test accuracy
for whichever model won — never a hand-picked or inflated number.

Usage:
    python ml/scripts/generate_dataset.py   # only needed once, or to regenerate
    python ml/scripts/train_model.py
"""
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
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

RF_PARAM_DISTRIBUTIONS = {
    "n_estimators": [200, 300, 400, 500, 600],
    "max_depth": [None, 12, 16, 20, 24, 30],
    "min_samples_split": [2, 3, 4, 5],
    "min_samples_leaf": [1, 2, 3],
    "max_features": ["sqrt", "log2", None],
}

# HistGradientBoostingClassifier's own tunables — kept to a smaller search
# budget than RF's because boosted trees are trained sequentially (one round
# per class per iteration across 52 classes), so each fit costs noticeably
# more than a Random Forest fit of comparable tree count.
GBM_PARAM_DISTRIBUTIONS = {
    "max_iter": [150, 200, 300],
    "max_depth": [6, 8, 10, None],
    "learning_rate": [0.05, 0.1, 0.15],
    "min_samples_leaf": [10, 20, 30],
    "l2_regularization": [0.0, 0.1, 0.5],
}


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"{DATASET_PATH} not found. Run generate_dataset.py first, "
            "or place a real dataset with matching columns there."
        )
    df = pd.read_csv(DATASET_PATH)
    assert df.isnull().sum().sum() == 0, "Unexpected missing values in the training dataset"
    return df


def _feature_importance_chart(feature_names: list, importances: np.ndarray, out_path: Path, model_name: str):
    order = np.argsort(importances)[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh([feature_names[i] for i in order][::-1], importances[order][::-1], color="#2E7D32")
    ax.set_xlabel("Permutation importance (mean accuracy drop)")
    ax.set_title(f"HealTheCrop crop model — feature importance ({model_name})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


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
    feature_names = NUMERIC_FEATURES + CATEGORICAL_FEATURES

    # 70/15/15 train/validation/test, stratified so every crop is represented
    # proportionally in all three splits. Validation picks the winning model
    # family; test is the untouched final number reported to the app.
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    print("Tuning Random Forest (5-fold CV, train split only)...")
    rf_search = RandomizedSearchCV(
        estimator=RandomForestClassifier(random_state=42, class_weight="balanced", n_jobs=-1),
        param_distributions=RF_PARAM_DISTRIBUTIONS,
        n_iter=25, cv=cv, scoring="accuracy", random_state=42, n_jobs=-1, refit=True,
    )
    rf_search.fit(X_train, y_train)
    rf_model = rf_search.best_estimator_
    print(f"  RF best CV accuracy: {rf_search.best_score_:.4f}, params: {rf_search.best_params_}")

    cv_gbm = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    print("Tuning HistGradientBoosting (3-fold CV, train split only)...")
    gbm_search = RandomizedSearchCV(
        estimator=HistGradientBoostingClassifier(random_state=42, class_weight="balanced"),
        param_distributions=GBM_PARAM_DISTRIBUTIONS,
        n_iter=12, cv=cv_gbm, scoring="accuracy", random_state=42, n_jobs=-1, refit=True,
    )
    gbm_search.fit(X_train, y_train)
    gbm_model = gbm_search.best_estimator_
    print(f"  GBM best CV accuracy: {gbm_search.best_score_:.4f}, params: {gbm_search.best_params_}")

    # Model selection happens on validation, never on test.
    rf_val_acc = accuracy_score(y_val, rf_model.predict(X_val))
    gbm_val_acc = accuracy_score(y_val, gbm_model.predict(X_val))
    rf_val_f1 = f1_score(y_val, rf_model.predict(X_val), average="weighted")
    gbm_val_f1 = f1_score(y_val, gbm_model.predict(X_val), average="weighted")
    print(f"Validation — RF: acc={rf_val_acc:.4f} f1={rf_val_f1:.4f} | GBM: acc={gbm_val_acc:.4f} f1={gbm_val_f1:.4f}")

    # Only switch away from Random Forest if HistGradientBoosting wins on
    # BOTH validation accuracy and weighted F1 — "consistently" better, not
    # just a coin-flip margin on one metric.
    gbm_wins = gbm_val_acc > rf_val_acc and gbm_val_f1 > rf_val_f1
    model_name = "hist_gradient_boosting" if gbm_wins else "random_forest"
    model = gbm_model if gbm_wins else rf_model
    best_params = gbm_search.best_params_ if gbm_wins else rf_search.best_params_
    print(f"Selected model family: {model_name}")

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")
    precision_macro = precision_score(y_test, y_pred, average="macro", zero_division=0)
    recall_macro = recall_score(y_test, y_pred, average="macro", zero_division=0)
    report = classification_report(
        y_test, y_pred, target_names=label_encoder.classes_, output_dict=True, zero_division=0
    )
    conf_matrix = confusion_matrix(y_test, y_pred, labels=range(len(label_encoder.classes_)))

    print(f"Held-out TEST accuracy ({model_name}): {accuracy:.4f}")
    print(f"Held-out TEST weighted F1: {f1:.4f}")
    print(f"Held-out TEST macro precision: {precision_macro:.4f}")
    print(f"Held-out TEST macro recall: {recall_macro:.4f}")

    # Permutation importance (computed on validation data, unbiased unlike RF's
    # built-in impurity importance, and works identically regardless of which
    # model family won — HistGradientBoostingClassifier has no
    # feature_importances_ attribute at all).
    print("Computing permutation importance on validation split...")
    perm = permutation_importance(model, X_val, y_val, n_repeats=10, random_state=42, n_jobs=-1)
    importances = perm.importances_mean
    importances = np.clip(importances, 0, None)
    importances_dict = dict(zip(feature_names, importances.round(4).tolist()))
    print("Feature importances (permutation):", json.dumps(importances_dict, indent=2))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    chart_path = MODEL_DIR / "feature_importance.png"
    _feature_importance_chart(feature_names, importances, chart_path, model_name)
    print(f"Saved feature importance chart to {chart_path}")

    # The multiclass model above answers "which single crop fits best?" — its
    # probabilities are relative (they sum to 100% across all crops), which is
    # correct for picking a winner but wrong for per-crop "confidence" cards:
    # a second crop can only look bad because the top one looks good, not
    # because it's actually unsuitable. A one-vs-rest ensemble of independent
    # binary classifiers (this crop vs. everything else) gives each crop its
    # own 0-100% model-based signal with no such coupling, reusing the winning
    # model family's tuned hyperparameters.
    print(f"Training one-vs-rest {model_name} classifiers for independent per-crop confidence...")
    if gbm_wins:
        # HistGradientBoostingClassifier has no n_jobs of its own (it manages
        # its own internal threading), so the outer OneVsRestClassifier loop
        # stays serial here to avoid oversubscribing CPU cores across all 52
        # classifiers at once.
        base_estimator = HistGradientBoostingClassifier(random_state=42, class_weight="balanced", **best_params)
        ovr_model = OneVsRestClassifier(base_estimator, n_jobs=1)
    else:
        # Each RF base estimator is single-threaded; parallelism instead comes
        # from OneVsRestClassifier fanning the 52 classifiers out across
        # cores during training. (At inference, app/ml/crop_predictor.py
        # forces n_jobs=1 on every fitted estimator anyway — calling
        # predict_proba() on 52 already-fitted single-row estimators doesn't
        # benefit from parallelism and re-spinning up worker pools 52 times
        # in a row per request was the actual bottleneck there, not here.)
        base_estimator = RandomForestClassifier(random_state=42, class_weight="balanced", n_jobs=1, **best_params)
        ovr_model = OneVsRestClassifier(base_estimator, n_jobs=-1)
    ovr_model.fit(X_train, y_train)
    print(f"Trained {len(ovr_model.estimators_)} independent one-vs-rest classifiers.")

    # Per-crop empirical feature statistics (mean, std), computed from the
    # TRAINING split only (never validation/test, to avoid leaking those rows
    # into a score used at inference time). This is the rule-based half of
    # the suitability score: how close the farmer's actual inputs are to what
    # this crop's own training rows typically look like, independent of what
    # the trained classifier "votes" for.
    train_df = X_train.copy()
    train_df["label"] = label_encoder.inverse_transform(y_train)
    crop_feature_stats = {}
    for crop, group in train_df.groupby("label"):
        crop_feature_stats[crop] = {
            feat: (float(group[feat].mean()), float(max(group[feat].std(), 1e-3)))
            for feat in NUMERIC_FEATURES
        }

    bundle = {
        "model": model,
        "model_name": model_name,
        "ovr_model": ovr_model,
        "label_encoder": label_encoder,
        "season_encoder": season_encoder,
        "location_encoder": location_encoder,
        "feature_names": feature_names,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "crop_feature_stats": crop_feature_stats,
        "metrics": {
            "accuracy": accuracy,
            "weighted_f1": f1,
            "precision_macro": precision_macro,
            "recall_macro": recall_macro,
            "validation_accuracy": rf_val_acc if not gbm_wins else gbm_val_acc,
            "cv_mean_accuracy": float(rf_search.best_score_ if not gbm_wins else gbm_search.best_score_),
            "cv_folds": cv.get_n_splits() if not gbm_wins else cv_gbm.get_n_splits(),
            "model_selected": model_name,
        },
        "feature_importances": importances_dict,
        "best_params": best_params,
    }
    model_path = MODEL_DIR / "crop_model.joblib"
    joblib.dump(bundle, model_path)
    print(f"Saved model bundle to {model_path}")

    metrics_path = MODEL_DIR / "training_report.json"
    metrics_path.write_text(json.dumps({
        "model_selected": model_name,
        "model_comparison": {
            "random_forest": {"validation_accuracy": rf_val_acc, "validation_weighted_f1": rf_val_f1, "cv_mean_accuracy": float(rf_search.best_score_), "best_params": rf_search.best_params_},
            "hist_gradient_boosting": {"validation_accuracy": gbm_val_acc, "validation_weighted_f1": gbm_val_f1, "cv_mean_accuracy": float(gbm_search.best_score_), "best_params": gbm_search.best_params_},
        },
        "accuracy": accuracy,
        "weighted_f1": f1,
        "precision_macro": precision_macro,
        "recall_macro": recall_macro,
        "cv_mean_accuracy": float(rf_search.best_score_ if not gbm_wins else gbm_search.best_score_),
        "cv_folds": cv.get_n_splits() if not gbm_wins else cv_gbm.get_n_splits(),
        "best_params": best_params,
        "feature_importances": importances_dict,
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
