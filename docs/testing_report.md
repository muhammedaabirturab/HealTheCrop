# Testing Report

## 1. ML model evaluation

Trained via [`ml/scripts/train_model.py`](../ml/scripts/train_model.py) on an 80/20
stratified split of the generated `crop_recommendation.csv` (3,300 rows, 22 crop classes,
150 samples/crop). Full metrics: [`ml/models/training_report.json`](../ml/models/training_report.json).

| Metric | Value |
|---|---|
| Accuracy | 96.36% |
| Weighted F1 | 0.9636 |
| Classes | 22 |
| Train / test rows | 2,640 / 660 |

Top feature importances: `humidity` (0.192), `season` (0.170), `rainfall` (0.156),
`nitrogen` (0.140), `potassium` (0.119), `phosphorus` (0.103), `temperature` (0.063),
`pH` (0.050), `location` (0.007) — season and humidity dominate, consistent with how the
synthetic per-crop agronomic profiles were constructed (see
[`ml/scripts/generate_dataset.py`](../ml/scripts/generate_dataset.py) for why the dataset
is generated rather than scraped, and how to substitute a real-world dataset).

## 2. Backend automated tests

18 pytest tests across auth, predictions, sensors, and reports/localization
([`backend/tests/`](../backend/tests/)), run against an isolated SQLite test database via
FastAPI's `TestClient`. All 18 pass.

```
tests/test_auth.py ..... (5 passed)
tests/test_predictions.py .... (4 passed)
tests/test_reports_and_localization.py ..... (5 passed)
tests/test_sensors.py .... (4 passed)
====== 18 passed ======
```

Coverage: registration/login/duplicate-email/wrong-password/auth-required paths; manual
prediction happy path + validation-range rejection + auth requirement + history; sensor
auto-registration + auth-gated device listing + 404 on unknown device; fertility scoring
for both deficient and healthy soil; full language list + translation bundle retrieval +
404 on unsupported language.

Also verified: `ruff check app --line-length=120` passes with zero findings.

## 3. Manual end-to-end verification (this session)

Performed against a live `uvicorn` instance:

- `GET /health` → `200`, reports `storage_backend` (confirms MinIO fallback-to-disk works
  when MinIO isn't running).
- Register → login → `GET /auth/me` round-trip.
- `POST /predictions/manual` with Kharif-season, high-nitrogen/rainfall input → correctly
  recommended **rice** at 90% confidence, matching the agronomic profile it was trained on.
- `POST /sensors/ingest` with a new `device_uid` → device auto-registered, reading stored.
- `POST /reports/soil-health` with deficient N/P/K and acidic pH → fertility score 55/100,
  5 targeted suggestions returned (nitrogen, phosphorus, potassium, pH, moisture).
- `POST /pest/scan` with a synthetic test image (green background + brown/black lesion
  circles) → heuristic detector correctly segmented and flagged 4 lesion regions with
  bounding boxes and plausible disease/pest matches, confirming the OpenCV fallback path
  works without any trained CNN present.

## 4. Frontend verification (this session)

Verified in a live browser session against the running backend:

- Landing page renders with the animated language selector; clicking any language
  (tested: Kannada) instantly re-renders the entire visible UI — hero title, nav labels,
  page copy — confirming i18next wiring across `en/hi/kn/ta/te/ml`.
- Registration → auto-login → redirect to Dashboard, which live-fetches `/health` and
  `/sensors/devices` from the backend.
- Manual Input → submit → 5 crop cards rendered with real confidence scores and, after a
  backend fix (see below), correct per-alternative metadata (image, season, water
  requirement, harvest duration, soil suitability, expected yield) rather than placeholders.
- No console errors on any tested page; network tab confirmed real API calls (not mocked).

**Bug found and fixed during this pass:** alternative crop cards initially showed
placeholder data because the backend only attached `crop_details` to the top recommendation.
Fixed in [`crop_predictor.py`](../backend/app/ml/crop_predictor.py) to attach metadata to
every alternative; schema and frontend updated to match; re-verified in-browser.

**Also found and fixed:** a directory-resolution off-by-one caused `crop_model.joblib`,
the fertility rules JSON, and the disease knowledge base to resolve one level above the
project root. Fixed by correcting `_BASE_DIR` in `crop_predictor.py`, `disease_service.py`,
and `fertility_service.py`.

## 5. Known limitations / not yet covered

- No automated frontend test suite (Playwright/Vitest) — verification was manual/browser-driven this session.
- The CNN pest-detection path (`cv/scripts/train_disease_model.py`) has not been exercised
  end-to-end since it requires a multi-GB PlantVillage-style dataset not included in this
  repo; only the always-available OpenCV heuristic path has been tested.
- Load/performance testing has not been performed.
- ESP32 firmware has been reviewed for correctness but not flashed to physical hardware in
  this environment (no device attached) — validate wiring and calibration values against
  your actual sensors before field deployment.
