# Scan Crop: Detection Model & Evaluation Methodology

## Current state: heuristic detector, not a trained CNN

`cv/models/` ships empty. `backend/app/cv/disease_service.py` checks for
`plant_disease_model.h5` + `class_indices.json` at startup; when they're
absent (as in this repo) it falls back to `heuristic_detector.py`, a
zero-dependency OpenCV color/blob analyzer:

1. Convert the leaf image to HSV and threshold it into four symptom masks —
   healthy green, chlorotic yellow, necrotic brown, black spot.
2. Find connected components ("lesions") in the three unhealthy masks.
3. Rank the dominant symptom color and map it to a short list of plausible
   diagnoses for that symptom pattern (`SYMPTOM_TO_CANDIDATES`), returning the
   top 3, with confidence derived from lesion area (not a statistical
   probability from a trained classifier).

This is useful as an always-available fallback and a real, non-fabricated
signal (it genuinely measures color/lesion patterns in the uploaded image),
but it is a color-segmentation heuristic, not a disease classifier — it
cannot distinguish two diseases that produce the same color of lesion, and
its "confidence" is a proxy (lesion size), not a calibrated probability.

## Why a CNN wasn't trained in this pass

Training a real classifier requires three things this environment doesn't
have:

- **A labeled image dataset.** No dataset ships in the repo (by design —
  PlantVillage alone is ~2GB), and this environment has no working path to
  pull one in automatically (Kaggle requires an API key; direct mirrors
  weren't verified here).
- **A GPU.** `tf.config.list_physical_devices('GPU')` returns empty in this
  environment. Training EfficientNetB0 on tens of thousands of images on CPU
  alone would take on the order of many hours to days, not something to run
  unattended inside this session.
- **TensorFlow itself isn't installed** in the backend virtualenv used here
  (`cv/requirements.txt` lists it for the training script's own environment,
  separate from the lighter backend runtime).

Rather than fabricate training logs or claim an accuracy number that was
never measured, this is stated plainly: **no CNN has been trained for this
repo.** What's been done instead is preparing the training script so that,
given a GPU and a dataset, running it produces a real model with real
metrics — see below.

## What changed in `cv/scripts/train_disease_model.py`

- **Backbone swapped from MobileNetV2 to EfficientNetB0.** EfficientNetB0
  reaches meaningfully higher ImageNet top-1 accuracy (~77% vs ~71-72%) at a
  similar parameter count, and that generally transfers into stronger leaf
  feature extraction after fine-tuning. An ensemble (e.g. EfficientNetB0 +
  ViT) was considered per the original request, but wasn't adopted as the
  default — ensembling roughly doubles training/inference cost and its
  accuracy benefit is dataset-dependent; it's a good follow-up experiment
  once a single strong baseline's real numbers are in hand, not a default to
  ship unverified.
- **Held-out `test/` split + real evaluation metrics.** The script now
  computes accuracy, per-class precision/recall/F1 (via
  `sklearn.metrics.classification_report`), and a full confusion matrix on a
  `datasets/plantvillage/test/` split if present, writing them to
  `cv/models/evaluation_report.json`. Training-loss curves alone don't tell
  you whether the model is production-ready; this does.
- **Lab-only vs. field images**, addressed directly in the script's
  docstring: PlantVillage is almost entirely lab photos (plain background,
  controlled light), and a model trained only on it will look great in
  validation and then fail on real farmer photos. The docstring recommends
  mixing in [PlantDoc](https://github.com/pratikkayal/PlantDoc-Dataset)
  (~2,600 images, overlapping classes, photographed in real field
  conditions — cluttered backgrounds, natural lighting, multiple angles) into
  train/val, or at minimum using it as a separate test split so reported
  metrics reflect field performance rather than lab performance.

## How to actually train it

```bash
pip install -r cv/requirements.txt
# Arrange datasets/plantvillage/{train,val,test}/<ClassName>/*.jpg
# (class names should match cv/data/disease_knowledge_base.json keys)
python cv/scripts/train_disease_model.py
```

On completion: `cv/models/plant_disease_model.h5`, `class_indices.json`, and
`evaluation_report.json` are written. `disease_service.py` picks up the model
automatically on next backend restart — no code change needed to switch from
heuristic to CNN inference.

## Recommended real-world validation before trusting this in production

Per the original request, before relying on any trained model:

1. Run it against a diverse held-out set — different crops, diseases, insect
   pests, lighting, camera angles, backgrounds, healthy plants, and severely
   infected plants — not just a random split of the training distribution.
2. Report accuracy, precision, recall, F1, and the confusion matrix (the
   script now does this automatically for the `test/` split).
3. Specifically check performance on field-condition photos (PlantDoc or
   your own farmer-submitted images) separately from lab-condition photos,
   since the gap between the two is usually the single biggest source of
   real-world disappointment with plant-disease classifiers.
4. Only raise `CONFIDENCE_UNCERTAIN_THRESHOLD` trust once the confusion
   matrix shows the model isn't systematically confusing visually-similar
   diseases (e.g. early vs. late blight) at a rate that would mislead a
   farmer's treatment choice.
