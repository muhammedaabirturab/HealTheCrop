# Installation Guide

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- Git
- (Optional, for production-like local setup) Docker + Docker Compose
- (Optional, for real hardware) Arduino IDE or PlatformIO + ESP32-WROOM-32 board

## 1. Clone the repository

```bash
git clone https://github.com/muhammedaabirturab/HealTheCrop.git
cd HealTheCrop
```

## 2. Train the ML crop recommendation model

The Random Forest model is trained from a generated dataset (see
[`ml/scripts/generate_dataset.py`](../ml/scripts/generate_dataset.py) for why it's generated
rather than scraped, and how to swap in a real dataset).

```bash
cd ml
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_dataset.py
python scripts/train_model.py
cd ..
```

This produces `datasets/crop_recommendation.csv` and `ml/models/crop_model.joblib` — both
are already committed to the repo, so **this step is optional** unless you want to retrain
with different parameters or a real-world dataset.

## 3. Backend setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The backend starts on `http://localhost:8000`. Swagger UI: `http://localhost:8000/docs`.
SQLite is used by default (`healthecrop.db`, auto-created). MinIO is optional in
development — if it isn't running, uploads transparently fall back to local disk under
`backend/storage/local/`.

To run the test suite:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## 4. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## 5. (Optional) Pest/disease CNN

The pest-scan feature works immediately using a built-in OpenCV heuristic. To use a trained
CNN instead, see [`cv/scripts/train_disease_model.py`](../cv/scripts/train_disease_model.py)
— you'll need a PlantVillage-style labeled image dataset (not included, ~2GB).

```bash
cd cv
pip install -r requirements.txt
python scripts/train_disease_model.py
```

The backend automatically prefers `cv/models/plant_disease_model.h5` once it exists.

## 6. (Optional) ESP32 hardware

See [`esp32/README.md`](../esp32/README.md) for wiring, library installation, and
`config.h` setup (Wi-Fi credentials, backend URL).

## 7. (Optional) Full stack via Docker Compose

```bash
docker compose up --build
```

Starts Postgres, MinIO, backend (port 8000), and frontend (port 4173). See
[Deployment Guide](deployment.md) for production configuration.
