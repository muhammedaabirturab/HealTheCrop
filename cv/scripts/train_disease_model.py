"""
Trains the HealTheCrop plant disease/pest classifier via transfer learning on
EfficientNetB0, in the style of the public PlantVillage dataset layout.

EfficientNetB0 replaces the earlier MobileNetV2 baseline — it gets meaningfully
higher ImageNet top-1 accuracy at a similar parameter count, which transfers
into better leaf-disease feature extraction after fine-tuning. Swap the
`build_model` backbone (e.g. to ConvNeXtTiny or a ViT) if you have the compute
budget to compare architectures; this file keeps a single well-tuned backbone
rather than an ensemble, since an ensemble roughly multiplies training and
inference cost for a gain that hasn't been validated against your own data.

Expected directory layout (not included in this repo due to size ~2GB+):

    datasets/plantvillage/
        train/
            Tomato___Early_blight/*.jpg
            Tomato___Late_blight/*.jpg
            Healthy/*.jpg
            ...
        val/
            Tomato___Early_blight/*.jpg
            ...
        test/
            Tomato___Early_blight/*.jpg
            ...

Class folder names should match the keys in cv/data/disease_knowledge_base.json
so predictions map directly onto treatment/prevention info.

IMPORTANT — lab vs. field images: PlantVillage alone is almost entirely
laboratory photos (uniform background, controlled lighting), which trains a
model that overfits to that setting and degrades badly on real farmer photos.
For a model that holds up in the field, mix in a field-condition dataset such
as PlantDoc (~2,600 images, same/overlapping classes, photographed in situ
with cluttered backgrounds and variable lighting — see
https://github.com/pratikkayal/PlantDoc-Dataset) into both train/ and val/,
or at minimum use it as a second, separate test/ split so the reported metrics
reflect real-world performance rather than lab-only performance.

Setup and run:

    pip install -r cv/requirements.txt
    python cv/scripts/train_disease_model.py

Produces:
    cv/models/plant_disease_model.h5   — the trained Keras model
    cv/models/class_indices.json       — index -> class name mapping
    cv/models/evaluation_report.json   — accuracy, precision/recall/F1 per
                                          class, and confusion matrix on the
                                          held-out test/ split

backend/app/cv/disease_service.py automatically picks up the .h5 model and
prefers it over the OpenCV heuristic fallback once both files are present.
"""
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow.keras import layers, models
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras.preprocessing.image import ImageDataGenerator

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datasets" / "plantvillage"
MODEL_DIR = ROOT / "cv" / "models"
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS_HEAD = 10
EPOCHS_FINE_TUNE = 10


def build_model(num_classes: int) -> tuple[tf.keras.Model, tf.keras.Model]:
    base = EfficientNetB0(input_shape=IMG_SIZE + (3,), include_top=False, weights="imagenet")
    base.trainable = False

    inputs = layers.Input(shape=IMG_SIZE + (3,))
    x = preprocess_input(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = models.Model(inputs, outputs)
    model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
    return model, base


def evaluate(model: tf.keras.Model, test_gen, class_names: list[str]) -> dict:
    """Computes accuracy, per-class precision/recall/F1, and a confusion
    matrix on a held-out split — required before trusting this model on real
    farmer photos, not just training-loss curves."""
    test_gen.reset()
    y_true = test_gen.classes
    y_pred_probs = model.predict(test_gen, verbose=0)
    y_pred = np.argmax(y_pred_probs, axis=1)

    report = classification_report(
        y_true, y_pred, target_names=class_names, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y_true, y_pred).tolist()

    return {
        "accuracy": report["accuracy"],
        "macro_avg": report["macro avg"],
        "weighted_avg": report["weighted avg"],
        "per_class": {name: report[name] for name in class_names},
        "confusion_matrix": matrix,
        "class_order": class_names,
    }


def train():
    train_dir = DATA_DIR / "train"
    val_dir = DATA_DIR / "val"
    test_dir = DATA_DIR / "test"
    if not train_dir.exists():
        raise FileNotFoundError(
            f"{train_dir} not found. Download a leaf-disease image dataset "
            "(e.g. PlantVillage + PlantDoc for field conditions) and arrange it "
            "as documented in this file's docstring."
        )

    train_gen = ImageDataGenerator(
        rotation_range=25, width_shift_range=0.1, height_shift_range=0.1,
        shear_range=0.1, zoom_range=0.15, horizontal_flip=True,
    ).flow_from_directory(train_dir, target_size=IMG_SIZE, batch_size=BATCH_SIZE, class_mode="categorical")

    val_gen = ImageDataGenerator().flow_from_directory(
        val_dir, target_size=IMG_SIZE, batch_size=BATCH_SIZE, class_mode="categorical"
    )

    num_classes = train_gen.num_classes
    model, base = build_model(num_classes)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=4, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(patience=2, factor=0.5),
    ]

    model.fit(train_gen, validation_data=val_gen, epochs=EPOCHS_HEAD, callbacks=callbacks)

    # Fine-tune the top layers of the base network
    base.trainable = True
    for layer in base.layers[:-40]:
        layer.trainable = False
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-5), loss="categorical_crossentropy", metrics=["accuracy"])
    model.fit(train_gen, validation_data=val_gen, epochs=EPOCHS_FINE_TUNE, callbacks=callbacks)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_DIR / "plant_disease_model.h5")

    class_indices = {v: k for k, v in train_gen.class_indices.items()}
    (MODEL_DIR / "class_indices.json").write_text(json.dumps(class_indices, indent=2))
    print(f"Saved model to {MODEL_DIR / 'plant_disease_model.h5'}")
    print(f"Saved class mapping to {MODEL_DIR / 'class_indices.json'}")

    if test_dir.exists():
        test_gen = ImageDataGenerator().flow_from_directory(
            test_dir, target_size=IMG_SIZE, batch_size=BATCH_SIZE, class_mode="categorical", shuffle=False
        )
        class_names = [class_indices[i] for i in range(num_classes)]
        report = evaluate(model, test_gen, class_names)
        (MODEL_DIR / "evaluation_report.json").write_text(json.dumps(report, indent=2))
        print(f"Test accuracy: {report['accuracy']:.4f}")
        print(f"Saved evaluation report to {MODEL_DIR / 'evaluation_report.json'}")
    else:
        print(f"No {test_dir} found — skipping held-out evaluation. "
              "Add a test/ split (ideally including field-condition images) to get real metrics.")


if __name__ == "__main__":
    train()
