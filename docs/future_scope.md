# Future Scope

## Machine Learning
- Replace the synthetically generated crop dataset with a real-world, region-specific
  agronomic dataset (soil survey + yield records) for production-grade accuracy.
- Add a regression model for expected yield estimation, not just crop classification.
- Online learning loop: let agronomists confirm/correct predictions to retrain periodically.

## Computer Vision
- Train the MobileNetV2 CNN on a real PlantVillage-style dataset (or a locally collected
  one) and ship the trained weights; benchmark against the OpenCV heuristic baseline.
- Multi-instance detection: segment and classify multiple distinct lesions/pests in one
  image independently (the heuristic already returns per-lesion bounding boxes; a trained
  object-detection model, e.g. YOLO, would improve per-instance accuracy).
- On-device inference (TensorFlow Lite) for offline pest scanning in low-connectivity areas.

## IoT / Hardware
- Low-power firmware variant: deep-sleep the ESP32 between readings and switch sensor VCC
  through a MOSFET to extend FC-28/pH probe lifespan and battery life.
- Solar-powered field node with battery monitoring reported alongside sensor data.
- LoRaWAN option for sensor nodes in areas without reliable Wi-Fi coverage.
- Real NPK sensor field calibration against lab soil test results.

## Platform
- SMS/USSD fallback channel for farmers without smartphones.
- Offline-first PWA data queueing (submit manual inputs while offline, sync when reconnected).
- Push notifications (via the PWA) for critical fertility/pest alerts.
- Admin analytics dashboard: regional crop trends, aggregated pest outbreak heatmaps.
- Marketplace integration: connect recommended crops to buyers/mandi price data.

## Voice & Accessibility
- Full text-to-speech playback of crop recommendations and treatment instructions in all
  six supported languages.
- Speech-to-text manual input entry for fully hands-free/illiterate-friendly operation.

## Infrastructure
- Multi-tenant support for cooperatives/FPOs managing many farmers' devices.
- Automated model retraining pipeline (CI-triggered) once enough confirmed-outcome data
  accumulates in `predictions`/`pest_detections`.
