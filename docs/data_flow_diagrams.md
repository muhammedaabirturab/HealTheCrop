# Data Flow Diagrams

## DFD Level 0 (Context Diagram)

```mermaid
flowchart LR
    Farmer((Farmer))
    Admin((Admin))
    ESP32["ESP32 Field Node"]
    System["HealTheCrop\nPlatform"]
    WeatherAPI["Weather API\n(optional)"]

    Farmer -->|"Soil data, photos, credentials"| System
    System -->|"Crop recommendations, pest reports,\ndashboards, alerts"| Farmer
    ESP32 -->|"Sensor readings (JSON)"| System
    System -->|"Device status"| ESP32
    Admin -->|"User/device management"| System
    System -->|"Analytics, reports"| Admin
    System -->|"Location + date"| WeatherAPI
    WeatherAPI -->|"Rainfall, season hints"| System
```

## DFD Level 1 (Major Processes)

```mermaid
flowchart TB
    Farmer((Farmer))
    ESP32["ESP32 Node"]

    P1["1.0 Authentication"]
    P2["2.0 Sensor Ingestion"]
    P3["3.0 Crop Recommendation"]
    P4["4.0 Pest & Disease Detection"]
    P5["5.0 Fertility Analysis"]
    P6["6.0 Reporting & History"]

    D1[("Users")]
    D2[("Devices /\nSensor Readings")]
    D3[("Predictions")]
    D4[("Pest Detections")]
    D5[("Fertility Reports")]
    D6[("Object Storage\n(images)")]

    Farmer -->|credentials| P1 --> D1
    ESP32 -->|readings| P2 --> D2
    Farmer -->|manual inputs| P3
    D2 -->|latest reading| P3
    P3 --> D3
    Farmer -->|photo upload| P4 --> D6
    P4 --> D4
    D2 -->|reading| P5 --> D5
    Farmer -->|view history| P6
    D3 --> P6
    D4 --> P6
    D5 --> P6
    P6 -->|dashboards| Farmer
```

## DFD Level 2 — Crop Recommendation (3.0) expanded

```mermaid
flowchart TB
    Input["Farmer input:\nN, P, K, temp, humidity,\npH, rainfall, season, location"]
    Season["3.1 Resolve Season\n(manual override or\ndate-based auto-detect)"]
    Encode["3.2 Encode categorical\nfeatures (season, location)"]
    Predict["3.3 Random Forest\ninference"]
    Rank["3.4 Rank top-5 crops\nby probability"]
    Enrich["3.5 Attach crop metadata\n(image, season, water,\nyield, soil suitability)"]
    Persist["3.6 Persist prediction\nrecord"]
    Output["Response: recommended crop,\nconfidence, alternatives,\nfeature importance"]

    Input --> Season --> Encode --> Predict --> Rank --> Enrich --> Persist --> Output
```

## DFD Level 2 — Pest & Disease Detection (4.0) expanded

```mermaid
flowchart TB
    Photo["Farmer photo upload"]
    Validate["4.1 Validate file\n(type, size ≤ 10MB)"]
    ModelCheck{"4.2 Trained CNN\navailable?"}
    CNN["4.3a MobileNetV2\ninference"]
    Heuristic["4.3b OpenCV color/blob\nheuristic analysis"]
    KB["4.4 Map result to\ndisease knowledge base"]
    Store["4.5 Store image in\nobject storage"]
    Persist["4.6 Persist detection\nrecord"]
    Output["Response: disease/pest name,\ntreatments, prevention, recovery time"]

    Photo --> Validate --> ModelCheck
    ModelCheck -->|yes| CNN --> KB
    ModelCheck -->|no| Heuristic --> KB
    Validate --> Store
    KB --> Persist --> Output
```
