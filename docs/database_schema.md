# Database Schema

Managed by SQLAlchemy models under [`backend/app/models/`](../backend/app/models/) and
versioned via Alembic migrations in [`backend/alembic/versions/`](../backend/alembic/versions/).
SQLite in development, PostgreSQL in production (same schema, different `DATABASE_URL`).

See [ER Diagram](er_diagram.md) for the visual relationship diagram.

## `users`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| name | varchar(120) | |
| email | varchar(255) | unique, indexed |
| hashed_password | varchar(255) | bcrypt via passlib |
| phone | varchar(20) | nullable |
| location | varchar(120) | nullable, used as ML input default |
| preferred_language | varchar(10) | default `en` |
| role | enum(`farmer`, `admin`) | default `farmer` |
| created_at | datetime | |

## `devices`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| device_uid | varchar(64) | unique, indexed — matches ESP32 firmware's `DEVICE_UID` |
| name | varchar(120) | default "ESP32 Field Node" |
| location | varchar(120) | nullable |
| owner_id | FK → users.id | nullable (auto-registered devices start unowned) |
| status | varchar(20) | `online` / `offline` |
| last_seen | datetime | nullable |
| created_at | datetime | |

## `sensor_readings`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| device_id | FK → devices.id | |
| nitrogen, phosphorus, potassium | float | nullable — ESP32 sends `null` for unattached sensors |
| moisture, temperature, humidity, ph, rainfall | float | nullable |
| recorded_at | datetime | |

## `predictions`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| user_id | FK → users.id | |
| input_features | JSON | the 7 numeric features used for prediction |
| recommended_crop | varchar(60) | |
| confidence | float | 0.0–1.0 |
| alternatives | JSON | top-5 `{crop, confidence, crop_details}` list |
| season | varchar(20) | nullable |
| source | varchar(20) | `manual` or `sensor` |
| created_at | datetime | |

## `pest_detections`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| user_id | FK → users.id | |
| image_key | varchar(255) | storage key, e.g. `minio://healthecrop-images/<uuid>.jpg` or `local://...` |
| detections | JSON | list of detection objects (name, confidence, treatments, etc.) |
| model_used | varchar(20) | `heuristic` or `cnn` |
| top_confidence | float | nullable |
| created_at | datetime | |

## `fertility_reports`

| Column | Type | Notes |
|---|---|---|
| id | integer, PK | |
| user_id | FK → users.id | |
| sensor_reading_id | FK → sensor_readings.id | nullable |
| fertility_score | float | 0–100 |
| issues | JSON | list of flagged indicator names |
| suggestions | JSON | fertility improvement suggestion objects |
| created_at | datetime | |
