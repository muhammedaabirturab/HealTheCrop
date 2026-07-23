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

## 5. UI/UX and stability pass (follow-up session)

A dedicated hardening pass focused on production-quality polish, root-causing rather than
suppressing errors, and re-testing the ML pipeline with realistic agronomic inputs.

**Bugs found and fixed:**

- **CORS fragility**: the backend only allow-listed `localhost:5173`/`:4173`. Vite silently
  picks the next free port (5174, 5175, ...) whenever the default is taken, which failed
  CORS preflight with no useful error — it just looked like "the backend is broken." Fixed
  by adding `allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+"` in
  [`main.py`](../backend/app/main.py) (loopback-only, so production security is unaffected).
- **Unvalidated soil-health input**: `/reports/soil-health` accepted a raw `dict` body with
  no type checking; a wrong type (e.g. a string where a number was expected) caused an
  uncaught `TypeError` and a raw 500. Replaced with a proper `SoilHealthRequest` Pydantic
  schema ([`schemas/report.py`](../backend/app/schemas/report.py)) so bad input now returns
  a clean 422. Covered by two new tests in `test_reports_and_localization.py`.
- **Pest-scan crash on missing filename**: `file.filename.split(".")` would raise
  `AttributeError` if `filename` were falsy. Fixed with a safe default in
  [`pest.py`](../backend/app/api/v1/pest.py); regression-tested in `test_pest.py`.
- **No global exception handler**: an unexpected exception anywhere in the API previously
  surfaced as a bare 500 with no guaranteed JSON shape. Added a catch-all handler in
  `main.py` that always returns `{"detail": "..."}` and logs the real traceback server-side.
- **Silent frontend error handling**: several pages (`Dashboard`, `History`) had `.catch()`
  blocks that swallowed errors with no user feedback, and others (`ManualInput`, `PestScan`)
  showed the same generic message regardless of whether the problem was a network failure,
  an expired session, or a validation error. Added a shared
  [`lib/errors.ts`](../frontend/src/lib/errors.ts) helper that inspects the Axios error
  shape and returns a specific, translated message, plus loading/error states on every page
  that fetches data.
- **Language-selector animation froze on first language**: the cycling animation used
  `framer-motion`'s `AnimatePresence` with `mode="wait"`, keyed on language code. In this
  environment, exit animations never completed (elements piled up in the DOM instead of
  unmounting), so `mode="wait"` waited forever and the display froze on the first language.
  Confirmed via DOM/state instrumentation before rewriting the cross-fade as a plain CSS
  opacity transition (no unmount step to get stuck on) — see
  [`LanguageSelector.tsx`](../frontend/src/components/LanguageSelector.tsx).
- **Language-selector settled-state collision**: the "has the user picked a language"
  check reused the same `localStorage` key react-i18next's `LanguageDetector` auto-caches
  the *detected* browser language to — which happens on every load, including a genuine
  first visit. That made the animation start in the already-"settled" state immediately,
  so it never cycled for new users. Fixed by tracking explicit choices under a separate
  dedicated key, written only inside the click handler.
- **Missing i18n key**: the Manual Input form's rainfall label was hardcoded in English
  (`'Rainfall (mm)'`) instead of using a translation key, breaking multilingual completeness
  for that one field. Added `dashboard.rainfall` across all six locale files.

**Re-verified after fixes** (live browser + curl against a running instance): manual
prediction with several realistic scenarios (rice paddy, chickpea, cotton — matching the
sanity-check cases below), soil-health with valid and invalid payloads, CORS preflight from
a non-default port, 404 handling with malformed device IDs, full registration → login →
manual input → crop card flow, and the language selector cycling through all six languages
continuously, stopping and persisting correctly (including across a full page reload) once
a language is explicitly chosen.

## 6. Realistic model sanity check

[`ml/scripts/sanity_check.py`](../ml/scripts/sanity_check.py) hand-picks eight realistic
real-world input combinations (not placeholder values) for known crops — e.g. a West Bengal
Kharif rice paddy (high N, high humidity, heavy monsoon rainfall), a Himalayan apple orchard
(very high P/K, cold, high humidity), a black-cotton-soil Kharif cotton field — and checks
the model's top prediction against domain expectations. Result: **8/8 matched**, all at
96–100% confidence, confirming the model's decision boundaries are agronomically sensible
and not just numerically accurate against its own synthetic training distribution.

## 7. Farmer-friendly seasons, real crop images, and recommendation reasoning

A follow-up pass replaced the Kharif/Rabi/Zaid season dropdown with universally recognizable
calendar seasons, added real photos for every crop, and made recommendations explain
themselves.

**Season mapping**: [`app/utils/season.py`](../backend/app/utils/season.py) now exposes a
`resolve_season()` that accepts spring/summer/autumn/winter from the UI and maps each to the
Kharif/Rabi/Zaid category the trained model actually expects
(`spring→Zaid, summer→Kharif, autumn→Kharif, winter→Rabi`), returning both values so the API
response echoes back the farmer's own season choice rather than the internal category.
Verified: all four UI seasons produce correct, agronomically sensible predictions (e.g.
winter + cold/high-P/K/humidity inputs → apple at 99% confidence; summer + hot/humid/high-
rainfall inputs → rice), and an unrecognized or omitted season falls back to calendar-based
auto-detection. 8 new backend tests cover the mapping table, case-insensitivity, and
boundary months.

**Real crop images**: all 22 crops now have an actual representative photo (previously a
generic icon), fetched from Wikipedia/Wikimedia Commons lead images via
[`ml/scripts/fetch_crop_images.py`](../ml/scripts/fetch_crop_images.py) — chosen over an
arbitrary image search because Commons images carry a clear, checkable, reusable license.
Verified in-browser: every card's `GET /crop-images/<crop>.jpg` request returns `200 OK`.

**Recommendation reasoning**: `build_explanation()` in
[`crop_predictor.py`](../backend/app/ml/crop_predictor.py) picks the top 1–2 numeric features
by the model's global feature importance, classifies each as ideal/low/high against a rough
comfort range, and returns *structured data* (crop, season, factor list) rather than a
hardcoded English sentence — the frontend's
[`lib/explanation.ts`](../frontend/src/lib/explanation.ts) composes the final sentence from
translated phrase templates so it reads correctly in all 6 supported languages, not just
English.

**Bug found and fixed during this pass:** the first implementation of `composeExplanation`
looked up translation keys like `featureHumidity` and `levelIdeal` without their
`cropRecommendation.` namespace prefix, so the UI showed raw key names instead of translated
text (e.g. "your soil has featureHumidity levelIdeal" instead of "a humidity level that is
ideal for this crop"). Caught via live browser testing, fixed, and re-verified in both
English and Hindi.

## 8. Known limitations / not yet covered

- No automated frontend test suite (Playwright/Vitest) — verification was manual/browser-driven this session.
- The CNN pest-detection path (`cv/scripts/train_disease_model.py`) has not been exercised
  end-to-end since it requires a multi-GB PlantVillage-style dataset not included in this
  repo; only the always-available OpenCV heuristic path has been tested.
- Load/performance testing has not been performed.
- ESP32 firmware has been reviewed for correctness but not flashed to physical hardware in
  this environment (no device attached) — validate wiring and calibration values against
  your actual sensors before field deployment.
