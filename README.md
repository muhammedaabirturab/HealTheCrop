# 🌾 HealTheCrop

**An Intelligent IoT & AI-Powered Smart Farming Platform**

HealTheCrop helps farmers monitor soil health, receive AI-driven crop recommendations,
detect pests and plant diseases from photos, and improve soil fertility — through an
interface designed for low-literacy, multilingual rural users, backed by real ESP32 field
hardware.

> Final-year engineering project: full-stack web app + PWA, FastAPI backend, Random Forest
> crop recommendation model, computer-vision pest/disease detection, ESP32 firmware, local
> object storage, and complete documentation/diagrams.

---

## Features

- **Soil health dashboard** — live sensor values, historical trend charts, color-coded
  fertility indicators (excellent/good/average/poor/critical).
- **AI crop recommendation** — Random Forest classifier trained on N-P-K, temperature,
  humidity, pH, rainfall, season, and location; returns top crop + top-5 alternatives with
  confidence scores and feature importance.
- **Pest & disease detection** — upload a leaf/fruit/stem photo; get disease/pest name,
  description, organic + chemical treatment, recommended pesticides, prevention tips, and
  expected recovery time. Works out of the box via an OpenCV heuristic detector, and
  upgrades automatically to a trained MobileNetV2 CNN if you train one (see
  [`cv/scripts/train_disease_model.py`](cv/scripts/train_disease_model.py)).
- **Fertility improvement engine** — rule-based recommendations (organic/chemical
  fertilizer, compost, crop rotation, micronutrients) with why/how/expected-improvement/time.
- **Manual input mode** — full prediction flow without any IoT hardware, for demos/testing.
- **ESP32 IoT integration** — real firmware for FC-28 soil moisture, DHT11 temp/humidity,
  analog pH sensor, and optional RS485 NPK sensor, with Wi-Fi auto-reconnect and graceful
  sensor-failure handling.
- **6-language support** — English, Hindi, Kannada, Tamil, Telugu, Malayalam — full i18n,
  with an animated language selector designed for users who may not read any of them fluently.
- **PWA** — installable, works on desktop/tablet/Android.
- **Local cloud storage** — MinIO (S3-compatible) for images/reports, with automatic
  fallback to local disk when MinIO isn't running (dev-friendly).

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS v4 + Framer Motion + react-i18next |
| Backend | FastAPI + SQLAlchemy 2.0 + Alembic + JWT auth |
| ML | scikit-learn (Random Forest), pandas, joblib |
| Computer Vision | OpenCV (heuristic, ships today) + TensorFlow/MobileNetV2 (optional trained CNN) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Object storage | MinIO (S3-compatible), local-disk fallback |
| IoT firmware | ESP32-WROOM-32 (Arduino framework, C++) |
| Deployment | Docker Compose (backend, frontend, Postgres, MinIO) |

## Project Structure

```
HealTheCrop/
├── frontend/        React + TS + Vite PWA
├── backend/         FastAPI application, tests, Alembic migrations
├── ml/              Crop recommendation dataset generation + Random Forest training
├── cv/              Plant disease knowledge base + CNN training script
├── esp32/           ESP32 Arduino firmware + wiring README
├── localization/    Canonical translation JSON (en, hi, kn, ta, te, ml)
├── database/        (Alembic migrations live in backend/alembic; schema doc below)
├── docs/            Documentation (this folder)
├── diagrams/         — see docs/, diagrams are embedded as Mermaid
├── datasets/        Generated crop_recommendation.csv
└── docker-compose.yml
```

## Quickstart

See [`docs/installation.md`](docs/installation.md) for full setup. Short version:

```bash
# 1. Train the crop recommendation model
cd ml && python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_dataset.py
python scripts/train_model.py

# 2. Run the backend
cd ../backend && python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# 3. Run the frontend
cd ../frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173. API docs (Swagger UI) are at http://localhost:8000/docs.

## Documentation

- [Installation Guide](docs/installation.md)
- [User Manual](docs/user_manual.md)
- [Deployment Guide](docs/deployment.md)
- [API Documentation](docs/api_documentation.md)
- [Database Schema](docs/database_schema.md)
- [System Architecture](docs/system_architecture.md)
- [Data Flow Diagrams (DFD 0/1/2)](docs/data_flow_diagrams.md)
- [ER Diagram](docs/er_diagram.md)
- [UML Diagrams](docs/uml_diagrams.md)
- [Hardware Wiring](docs/hardware_wiring.md)
- [Testing Report](docs/testing_report.md)
- [Future Scope](docs/future_scope.md)

## License

Educational / final-year academic project. Add a license of your choice before public reuse.
