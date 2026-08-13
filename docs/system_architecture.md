# System Architecture

```mermaid
flowchart TB
    subgraph Field["Field Hardware"]
        S1[FC-28 Soil Moisture]
        S2[DHT11 Temp/Humidity]
        S3[Analog pH Sensor]
        S4["NPK Sensor (optional, RS485)"]
        ESP32["ESP32-WROOM-32\n(USB serial only —\nno Wi-Fi/Bluetooth)"]
        S1 --> ESP32
        S2 --> ESP32
        S3 --> ESP32
        S4 --> ESP32
    end

    subgraph Backend["FastAPI Backend"]
        API["REST API\n(auth, sensors, predictions,\npest, reports, localization)"]
        ML["ML Module\nRandom Forest\ncrop predictor"]
        CV["CV Module\nOpenCV heuristic /\nMobileNetV2 CNN"]
        Fertility["Fertility Engine\n(rule-based)"]
        Storage["Storage Service\n(MinIO client +\nlocal-disk fallback)"]
        DB[(PostgreSQL / SQLite)]
        API --> ML
        API --> CV
        API --> Fertility
        API --> Storage
        API --> DB
    end

    subgraph ObjectStore["Local Cloud Storage"]
        MinIO[(MinIO\nS3-compatible)]
    end

    subgraph Frontend["React PWA"]
        UI["Dashboard, Manual Input,\nCrop Cards, Pest Scan,\nHistory, Auth"]
        i18n["i18next\n(en/hi/kn/ta/te/ml)"]
        UI --> i18n
    end

    Farmer((Farmer)) --> UI
    ESP32 -->|USB serial JSON\nWeb Serial API| UI
    UI -->|REST + JWT| API
    Storage --> MinIO
```

## Component responsibilities

- **ESP32 firmware** reads sensors on a fixed interval, tolerates individual sensor failures
  (sends `null` for that field rather than aborting), and communicates exclusively over USB
  serial — no Wi-Fi or Bluetooth. The browser reads the serial output directly (Web Serial
  API) and is the one that POSTs it to the backend.
- **Backend API** is organized into modules mirroring the spec's required separation:
  `auth`, `sensors`, `predictions` (ML), `pest` (CV), `reports` (fertility), `localization`,
  plus core `storage`/`database`/`security` concerns.
- **ML module** loads a pre-trained Random Forest bundle (`ml/models/crop_model.joblib`) once
  per process and serves predictions synchronously (sub-millisecond inference).
- **CV module** prefers a trained CNN if present, otherwise uses an always-available OpenCV
  color/blob heuristic — see [`backend/app/cv/`](../backend/app/cv/).
- **Storage service** talks to MinIO when reachable; transparently falls back to local disk
  otherwise, so development never blocks on having MinIO running.
- **Frontend** is a single-page React app with client-side routing, JWT stored via a
  persisted Zustand store, and full runtime language switching via i18next.
