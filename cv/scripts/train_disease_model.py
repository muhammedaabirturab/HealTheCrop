"""
Trains the HealTheCrop plant disease/pest classifier via transfer learning on
MobileNetV2, in the style of the public PlantVillage dataset layout.

Expected directory layout (not included in this repo due to size ~2GB):

    datasets/plantvillage/
        train/
            Tomato___Early_blight/*.jpg
            Tomato___Late_blight/*.jpg
            Healthy/*.jpg
            ...
        val/
            Tomato___Early_blight/*.jpg
            ...

Class folder names should match the keys in cv/data/disease_knowledge_base.json
so predictions map directly onto treatment/prevention info.

Download PlantVillage (or an equivalent labeled leaf-disease dataset), split
it into train/val folders per class under datasets/plantvillage/, then run:

    pip install -r cv/requirements.txt
    python cv/scripts/train_disease_model.py

Produces cv/models/plant_disease_model.h5 and cv/models/class_indices.json,
which backend/app/cv/disease_service.py automatically picks up and prefers
over the OpenCV heuristic fallback.
"""
import json
from pathlib import Path

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import ImageDataGenerator

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datasets" / "plantvillage"
MODEL_DIR = ROOT / "cv" / "models"
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS_HEAD = 10
EPOCHS_FINE_TUNE = 8


def build_model(num_classes: int) -> tf.keras.Model:
    base = MobileNetV2(input_shape=IMG_SIZE + (3,), include_top=False, weights="imagenet")
    base.trainable = False

    inputs = layers.Input(shape=IMG_SIZE + (3,))
    x = preprocess_input(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = models.Model(inputs, outputs)
    model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
    return model, base


def train():
    train_dir = DATA_DIR / "train"
    val_dir = DATA_DIR / "val"
    if not train_dir.exists():
        raise FileNotFoundError(
            f"{train_dir} not found. Download a leaf-disease image dataset "
            "(e.g. PlantVillage) and arrange it as documented in this file's docstring."
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
    for layer in base.layers[:-30]:
        layer.trainable = False
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-5), loss="categorical_crossentropy", metrics=["accuracy"])
    model.fit(train_gen, validation_data=val_gen, epochs=EPOCHS_FINE_TUNE, callbacks=callbacks)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_DIR / "plant_disease_model.h5")

    class_indices = {v: k for k, v in train_gen.class_indices.items()}
    (MODEL_DIR / "class_indices.json").write_text(json.dumps(class_indices, indent=2))

    print(f"Saved model to {MODEL_DIR / 'plant_disease_model.h5'}")
    print(f"Saved class mapping to {MODEL_DIR / 'class_indices.json'}")


if __name__ == "__main__":
    train()
